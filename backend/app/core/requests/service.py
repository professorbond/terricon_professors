"""Операции движка заявок. Все проверки прав — здесь, на сервере."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, rbac
from app.core.errors import conflict, forbidden, not_found, validation
from app.core.events import events
from app.core.ids import new_id
from app.core.org.models import Employee
from app.core.requests.models import (
    APPROVED,
    CANCELLED,
    ESCALATED,
    OPEN_STATUSES,
    REJECTED,
    SUBMITTED,
    Request,
    RequestEvent,
)
from app.core.requests.registry import request_types

DECISIONS = (APPROVED, REJECTED)


# ---------- права ----------


async def can_view(session: AsyncSession, viewer: Employee, req: Request) -> bool:
    if req.employee_id == viewer.id or viewer.role == rbac.HR:
        return True
    rtype = request_types.get(req.type)
    if not rtype.visible_to_manager:
        return False
    owner = await session.get(Employee, req.employee_id)
    return owner is not None and rbac.is_my_team(viewer, owner)


def can_decide(actor: Employee, req: Request) -> bool:
    if req.employee_id == actor.id or req.status not in OPEN_STATUSES:
        return False
    if req.status == ESCALATED or req.approver_kind == "hr":
        return actor.role == rbac.HR
    if req.approver_kind == "manager":
        return actor.id == req.approver_id
    return False


def can_cancel(actor: Employee, req: Request) -> bool:
    return req.employee_id == actor.id and req.status == SUBMITTED and request_types.get(req.type).cancellable


async def get_visible(session: AsyncSession, viewer: Employee, request_id: str) -> Request:
    """Заявка по id с проверкой доступа. Чужая заявка → 403 (по прямому id тоже)."""
    req = await session.get(Request, request_id)
    if req is None:
        raise not_found("Заявка не найдена")
    if not await can_view(session, viewer, req):
        raise forbidden("Нет доступа к этой заявке")
    return req


# ---------- создание ----------


async def _next_number(session: AsyncSession, prefix: str) -> str:
    year = clock.now().year
    like = f"{prefix}-{year}-%"
    count = await session.scalar(select(func.count()).select_from(Request).where(Request.number.like(like)))
    return f"{prefix}-{year}-{(count or 0) + 1:04d}"


def _add_event(
    req: Request,
    event: str,
    actor: Employee | None,
    comment: str | None = None,
    data: dict[str, Any] | None = None,
) -> RequestEvent:
    ev = RequestEvent(
        id=new_id(),
        request_id=req.id,
        at=clock.now(),
        actor_id=actor.id if actor else None,
        actor_kind="user" if actor else "system",
        event=event,
        status=req.status,
        comment=comment,
        data=data or {},
    )
    req.events.append(ev)
    return ev


async def add_note(
    session: AsyncSession, req: Request, event: str, data: dict[str, Any] | None = None, comment: str | None = None
) -> None:
    """Системная отметка в истории без смены статуса (например, «Срок ответа до …»)."""
    _add_event(req, event, None, comment, data)
    await session.flush()


async def find_by_submission_key(session: AsyncSession, employee: Employee, submission_key: str) -> Request | None:
    """Для идемпотентной отправки формы: модуль проверяет это до своей валидации."""
    q = select(Request).where(Request.employee_id == employee.id, Request.submission_key == submission_key)
    return (await session.scalars(q)).first()


async def create(
    session: AsyncSession,
    employee: Employee,
    type_code: str,
    payload: dict[str, Any],
    submission_key: str | None = None,
) -> Request:
    """Создать заявку. Идемпотентно по (employee, submission_key): повтор вернёт ту же заявку."""
    rtype = request_types.get(type_code)
    if submission_key:
        existing = await find_by_submission_key(session, employee, submission_key)
        if existing is not None:
            if existing.type != type_code:
                raise conflict("SUBMISSION_KEY_REUSED", "Ключ отправки уже использован")
            return existing

    approver_kind: str = rtype.approver
    approver_id: str | None = None
    status = SUBMITTED
    if approver_kind == "manager":
        approver_id = employee.manager_id
        if approver_id is None:  # нет руководителя — сразу к HR
            approver_kind = "hr"

    req = Request(
        id=new_id(),
        number=await _next_number(session, rtype.number_prefix),
        type=type_code,
        employee_id=employee.id,
        approver_kind=approver_kind,
        approver_id=approver_id,
        status=status,
        payload=payload,
        submission_key=submission_key,
        version=1,
        created_at=clock.now(),
        events=[],
    )
    session.add(req)
    _add_event(req, "created", employee)
    await session.flush()
    await events.emit("request.created", session=session, request=req, employee=employee)
    return req


# ---------- решение ----------


async def _apply_decision(
    session: AsyncSession,
    req: Request,
    actor: Employee | None,
    decision: str,
    reason_code: str | None,
    comment: str | None,
) -> Request:
    if decision not in DECISIONS:
        raise validation("UNKNOWN_DECISION", "Решение должно быть Approved или Rejected", "decision")
    if req.status not in OPEN_STATUSES:
        raise conflict("ALREADY_DECIDED", "По заявке уже принято решение", {"status": req.status})
    comment = (comment or "").strip() or None
    if decision == REJECTED and not comment:
        raise validation("COMMENT_REQUIRED", "Укажите причину отказа", "comment")

    # Модули (гарантии и др.) могут запретить решение, бросив AppError
    await events.emit(
        "request.before_decision",
        session=session,
        request=req,
        actor=actor,
        decision=decision,
        reason_code=reason_code,
        comment=comment,
        by_system=actor is None,
    )

    req.status = decision
    req.decided_at = clock.now()
    req.decided_by = actor.id if actor else None
    req.decided_by_system = actor is None
    req.decision_reason_code = reason_code
    req.decision_comment = comment
    req.version += 1
    _add_event(req, decision.lower(), actor, comment, {"reasonCode": reason_code} if reason_code else None)
    await session.flush()
    await events.emit("request.decided", session=session, request=req, actor=actor, by_system=actor is None)
    return req


async def decide(
    session: AsyncSession,
    actor: Employee,
    request_id: str,
    decision: str,
    expected_version: int | None = None,
    reason_code: str | None = None,
    comment: str | None = None,
) -> Request:
    req = await get_visible(session, actor, request_id)
    if not can_decide(actor, req):
        raise forbidden("Вы не можете принять решение по этой заявке")
    if expected_version is not None and expected_version != req.version:
        raise conflict("STALE_VERSION", "Заявка изменилась, обновите страницу", {"version": req.version})
    return await _apply_decision(session, req, actor, decision, reason_code, comment)


async def decide_by_system(
    session: AsyncSession, request_id: str, decision: str, reason: str, reason_code: str | None = None
) -> Request:
    """Решение по политике HR (гарантии, «Зарплата по факту»). reason — комментарий в историю."""
    req = await session.get(Request, request_id)
    if req is None:
        raise not_found("Заявка не найдена")
    return await _apply_decision(session, req, None, decision, reason_code, reason)


async def escalate_to_hr(session: AsyncSession, request_id: str, reason: str) -> Request:
    """Передать заявку HR (например, истёк срок ответа руководителя)."""
    req = await session.get(Request, request_id)
    if req is None:
        raise not_found("Заявка не найдена")
    if req.status != SUBMITTED:
        raise conflict("ALREADY_DECIDED", "Заявку нельзя передать HR в текущем статусе")
    req.status = ESCALATED
    req.version += 1
    _add_event(req, "escalated", None, reason)
    await session.flush()
    await events.emit("request.escalated", session=session, request=req)
    return req


async def cancel(session: AsyncSession, actor: Employee, request_id: str) -> Request:
    req = await get_visible(session, actor, request_id)
    if not can_cancel(actor, req):
        if req.status != SUBMITTED:
            raise conflict("ALREADY_DECIDED", "Отозвать можно только заявку на рассмотрении")
        raise forbidden("Эту заявку нельзя отозвать")
    req.status = CANCELLED
    req.version += 1
    _add_event(req, "cancelled", actor)
    await session.flush()
    await events.emit("request.cancelled", session=session, request=req, actor=actor)
    return req


# ---------- списки ----------


async def list_mine(session: AsyncSession, user: Employee, type_code: str | None = None) -> list[Request]:
    q = select(Request).where(Request.employee_id == user.id)
    if type_code:
        q = q.where(Request.type == type_code)
    return list(await session.scalars(q.order_by(Request.created_at.desc())))


async def list_inbox(
    session: AsyncSession, user: Employee, only_open: bool = True, type_code: str | None = None
) -> list[Request]:
    """Руководитель: заявки своей команды, где он согласующий. HR: адресованные HR и переданные HR."""
    if user.role == rbac.MANAGER:
        q = select(Request).where(Request.approver_id == user.id, Request.approver_kind == "manager")
    elif user.role == rbac.HR:
        q = select(Request).where((Request.approver_kind == "hr") | (Request.status == ESCALATED))
    else:
        raise forbidden()
    if only_open:
        q = q.where(Request.status.in_(OPEN_STATUSES))
    if type_code:
        q = q.where(Request.type == type_code)
    rows = list(await session.scalars(q.order_by(Request.created_at.desc())))
    if user.role == rbac.MANAGER:
        rows = [r for r in rows if request_types.get(r.type).visible_to_manager]
    return rows


async def list_all(
    session: AsyncSession, type_code: str | None = None, status: str | None = None, country: str | None = None
) -> list[Request]:
    """Реестр HR (вызывать только после проверки роли)."""
    q = select(Request)
    if type_code:
        q = q.where(Request.type == type_code)
    if status:
        q = q.where(Request.status == status)
    if country:
        q = q.join(Employee, Employee.id == Request.employee_id).where(Employee.country == country)
    return list(await session.scalars(q.order_by(Request.created_at.desc())))


__all__ = [
    "add_note",
    "can_cancel",
    "can_decide",
    "can_view",
    "cancel",
    "create",
    "decide",
    "decide_by_system",
    "escalate_to_hr",
    "find_by_submission_key",
    "get_visible",
    "list_all",
    "list_inbox",
    "list_mine",
]
