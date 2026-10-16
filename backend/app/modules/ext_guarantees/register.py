from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.modules import ModuleContext
from app.core.org.models import Employee
from app.core.requests.models import Request
from app.modules.ext_guarantees import service
from app.modules.ext_guarantees.models import RequestGuarantee
from app.modules.ext_guarantees.router import router
from app.modules.ext_guarantees.schemas import GuaranteeBadge

RU = {
    "notif.guarantee.deadline.title": "Ответ в срок",
    "notif.guarantee.deadline.body": "{number}: ответ до {deadline}",
    "notif.guarantee.overdue.title": "Срок ответа истёк",
    "notif.guarantee.overdue.body": "{number}: заявка ждёт решения HR дольше срока",
    "reason.STAFFING": "Не хватает людей в смене",
    "reason.PEAK_LOAD": "Пиковая нагрузка (распродажи)",
    "reason.TEAM_OVERLAP": "Пересечение с отпусками команды",
    "reason.LATE_NOTICE": "Заявка подана слишком поздно",
    "reason.NOT_HR_TOPIC": "Вопрос не относится к HR",
    "reason.OTHER": "Другая причина (в комментарии)",
}
KK = {
    "notif.guarantee.deadline.title": "Уақытында жауап",
    "notif.guarantee.deadline.body": "{number}: жауап {deadline} дейін",
    "notif.guarantee.overdue.title": "Жауап беру мерзімі өтті",
    "notif.guarantee.overdue.body": "{number}: өтінім HR шешімін мерзімнен ұзақ күтуде",
    "reason.STAFFING": "Ауысымда адам жетіспейді",
    "reason.PEAK_LOAD": "Жоғары жүктеме (сатылымдар)",
    "reason.TEAM_OVERLAP": "Команданың демалыстарымен қиылысу",
    "reason.LATE_NOTICE": "Өтінім тым кеш берілді",
    "reason.NOT_HR_TOPIC": "Сұрақ HR-ға қатысты емес",
    "reason.OTHER": "Басқа себеп (түсініктемеде)",
}


async def extend_request(session: AsyncSession, request: Request, viewer: Employee) -> dict[str, Any]:
    g = (await session.scalars(select(RequestGuarantee).where(RequestGuarantee.request_id == request.id))).first()
    if g is None:
        return {}
    decided_late = request.decided_at is not None and request.decided_at > g.deadline_at and g.resolution == "none"
    overdue = request.decided_at is None and clock.now() > g.deadline_at
    return {"guarantee": GuaranteeBadge(deadline_at=g.deadline_at, resolution=g.resolution, overdue=overdue, decided_late=decided_late)}


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.events.subscribe("request.created", service.on_created)
    ctx.events.subscribe("request.before_decision", service.before_decision)
    ctx.events.subscribe("request.decided", service.on_decided)
    ctx.ticks.register("ext_guarantees", service.tick)
    ctx.request_extensions.register(extend_request)
    ctx.include_router(router)
