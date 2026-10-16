"""Уведомления движка заявок по умолчанию: согласующему — о новой заявке, автору — о решении."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import EventBus
from app.core.i18n import register as register_i18n
from app.core.notifications import notify
from app.core.org.models import Employee
from app.core.org.service import list_hr
from app.core.requests.models import Request
from app.core.requests.registry import request_types

RU = {
    "request.anonymous_author": "Анонимный автор",
    "notif.request.new.title": "Новая заявка на согласование",
    "notif.request.new.body": "{type} {number} ждёт вашего решения",
    "notif.request.approved.title": "Заявка одобрена",
    "notif.request.approved.body": "{type} {number}: одобрено",
    "notif.request.approved_system.body": "{type} {number}: одобрено по политике HR",
    "notif.request.rejected.title": "Заявка отклонена",
    "notif.request.rejected.body": "{type} {number}: отказ. Причина: {comment}",
    "notif.request.escalated.title": "Заявка передана HR",
    "notif.request.escalated.body": "{type} {number} передана HR: {comment}",
}
KK = {
    "request.anonymous_author": "Аноним автор",
    "notif.request.new.title": "Келісуге жаңа өтінім",
    "notif.request.new.body": "{type} {number} сіздің шешіміңізді күтуде",
    "notif.request.approved.title": "Өтінім мақұлданды",
    "notif.request.approved.body": "{type} {number}: мақұлданды",
    "notif.request.approved_system.body": "{type} {number}: HR саясаты бойынша мақұлданды",
    "notif.request.rejected.title": "Өтінім қабылданбады",
    "notif.request.rejected.body": "{type} {number}: бас тартылды. Себебі: {comment}",
    "notif.request.escalated.title": "Өтінім HR-ға берілді",
    "notif.request.escalated.body": "{type} {number} HR-ға берілді: {comment}",
}


def _params(req: Request, **extra: str | None) -> dict[str, str | None]:
    # *_key — ключ i18n, переводится на языке получателя: {type}
    return {"type_key": request_types.get(req.type).title_key, "number": req.number, **extra}


def _target(req: Request) -> dict[str, str]:
    return {"kind": "request", "requestId": req.id}


async def _notify_hr(session: AsyncSession, req: Request, title_key: str, body_key: str, **extra: str | None) -> None:
    owner = await session.get(Employee, req.employee_id)
    # HR страны сотрудника; если в стране HR нет — всем HR
    hrs = await list_hr(session, owner.country if owner else None) or await list_hr(session)
    for hr in hrs:
        if hr.id != req.employee_id:
            await notify(session, hr.id, "request.inbox", title_key, body_key, _params(req, **extra), _target(req))


async def on_created(session: AsyncSession, request: Request, employee: Employee) -> None:
    if request.approver_kind == "manager" and request.approver_id:
        await notify(
            session,
            request.approver_id,
            "request.inbox",
            "notif.request.new.title",
            "notif.request.new.body",
            _params(request),
            _target(request),
        )
    elif request.approver_kind == "hr":
        await _notify_hr(session, request, "notif.request.new.title", "notif.request.new.body")


async def on_decided(session: AsyncSession, request: Request, actor: Employee | None, by_system: bool) -> None:
    if request.status == "Approved":
        body = "notif.request.approved_system.body" if by_system else "notif.request.approved.body"
        title = "notif.request.approved.title"
    else:
        title, body = "notif.request.rejected.title", "notif.request.rejected.body"
    await notify(
        session,
        request.employee_id,
        "request.decided",
        title,
        body,
        _params(request, comment=request.decision_comment),
        _target(request),
    )


async def on_escalated(session: AsyncSession, request: Request) -> None:
    comment = request.events[-1].comment if request.events else None
    await notify(
        session,
        request.employee_id,
        "request.escalated",
        "notif.request.escalated.title",
        "notif.request.escalated.body",
        _params(request, comment=comment),
        _target(request),
    )
    await _notify_hr(
        session, request, "notif.request.escalated.title", "notif.request.escalated.body", comment=comment
    )


def register(bus: EventBus) -> None:
    register_i18n(RU, KK)
    bus.subscribe("request.created", on_created)
    bus.subscribe("request.decided", on_decided)
    bus.subscribe("request.escalated", on_escalated)

