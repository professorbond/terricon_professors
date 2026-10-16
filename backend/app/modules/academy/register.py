from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.modules import ModuleContext
from app.core.org.models import Employee
from app.core.profile import TrainingSummary
from app.modules.academy import service
from app.modules.academy.models import Course
from app.modules.academy.router import router

RU = {
    "notif.academy.assigned.title": "Назначен курс",
    "notif.academy.assigned.body": "«{course}» — начните, когда будет удобно",
    "notif.academy.assigned.body_due": "«{course}» — пройти до {due}",
    "notif.academy.completed.title": "Курс пройден",
    "notif.academy.completed.body": "«{course}»: результат {score}%",
}
KK = {
    "notif.academy.assigned.title": "Курс тағайындалды",
    "notif.academy.assigned.body": "«{course}» — ыңғайлы кезде бастаңыз",
    "notif.academy.assigned.body_due": "«{course}» — {due} дейін өту",
    "notif.academy.completed.title": "Курс аяқталды",
    "notif.academy.completed.body": "«{course}»: нәтиже {score}%",
}


async def contribute_profile(session: AsyncSession, viewer: Employee, employee: Employee) -> dict[str, Any]:
    """Назначенное обучение в профиле (поле кейса). Видно тем же, кому виден профиль."""
    items = []
    for a in await service.list_assignments(session, employee.id):
        course = await session.get(Course, a.course_id)
        assert course is not None
        p = await service.progress(session, employee.id, course.id)
        items.append(
            TrainingSummary(
                course_id=course.id,
                title=service.title(course, viewer.lang),
                status=p.status,
                lessons_percent=p.lessons_percent,
                score_percent=p.score_percent,
                due_date=a.due_date,
            )
        )
    return {"assigned_training": items}


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.profile.register(contribute_profile)
    ctx.include_router(router)
