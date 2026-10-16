"""«Открытая лестница»: грейд, вилка, путь к следующему (CLAUDE.md §7.4). Флаг: ladder."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.modules import BackendModule, ModuleContext
from app.core.notifications import notify
from app.core.org.models import Employee
from app.modules.ext_ladder import service
from app.modules.ext_ladder.router import router
from app.modules.ext_ladder.seed import seed

RU = {
    "grade.SORT-1": "Сортировщик", "grade.SORT-2": "Старший сортировщик", "grade.LEAD-1": "Руководитель смены",
    "grade.HR-2": "HR-специалист", "grade.KG-SORT-1": "Сортировщик", "grade.KG-SORT-2": "Старший сортировщик",
    "grade.KG-LEAD-1": "Руководитель склада",
    "ladder.months_in_grade": "{n} мес в текущем грейде",
    "ladder.no_incidents": "{n} мес без замечаний",
    "notif.ladder.criterion.title": "Шаг к повышению",
    "notif.ladder.criterion.body": "Курс «{course}» засчитан для грейда «{grade}». Выполнено {done} из {total} условий",
    "notif.ladder.ready.title": "Все условия выполнены",
    "notif.ladder.ready.body": "Вы выполнили все условия для грейда «{grade}». HR рассмотрит переход при пересмотре",
}
KK = {
    "grade.SORT-1": "Сұрыптаушы", "grade.SORT-2": "Аға сұрыптаушы", "grade.LEAD-1": "Ауысым басшысы",
    "grade.HR-2": "HR маманы", "grade.KG-SORT-1": "Сұрыптаушы", "grade.KG-SORT-2": "Аға сұрыптаушы",
    "grade.KG-LEAD-1": "Қойма басшысы",
    "ladder.months_in_grade": "Қазіргі грейдте {n} ай",
    "ladder.no_incidents": "{n} ай ескертусіз",
    "notif.ladder.criterion.title": "Жоғарылауға қадам",
    "notif.ladder.criterion.body": "«{course}» курсы «{grade}» грейді үшін есептелді. {total} шарттың {done} орындалды",
    "notif.ladder.ready.title": "Барлық шарттар орындалды",
    "notif.ladder.ready.body": "«{grade}» грейдінің барлық шарттарын орындадыңыз",
}


async def on_course_completed(session: AsyncSession, employee: Employee, course: Any, **_: Any) -> None:
    """Курс из критериев лестницы → уведомление о выполненном шаге (или о готовности к переходу)."""
    lad = await service.ladder(session, employee, employee.lang)
    if lad.next is None or not any(c.kind == "course" and c.course_id == course.id for c in lad.criteria):
        return
    if lad.ready:
        await notify(session, employee.id, "ladder.ready", "notif.ladder.ready.title", "notif.ladder.ready.body", {"grade": lad.next.title})
    else:
        await notify(
            session, employee.id, "ladder.criterion", "notif.ladder.criterion.title", "notif.ladder.criterion.body",
            {"course": course.title, "grade": lad.next.title, "done": lad.criteria_done, "total": lad.criteria_total},
        )


async def contribute_profile(session: AsyncSession, viewer: Employee, employee: Employee) -> dict[str, Any]:
    """Лестница видна только самому сотруднику (в ней прибавка к его окладу)."""
    if viewer.id != employee.id:
        return {}
    return {"ladder": await service.ladder(session, employee, viewer.lang)}


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.events.subscribe("academy.course_completed", on_course_completed)
    ctx.profile.register(contribute_profile)
    ctx.include_router(router)


module = BackendModule(name="ext_ladder", feature="ladder", register=register, seed=seed, description="Открытая лестница")
