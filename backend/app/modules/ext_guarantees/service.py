"""Правила гарантий: срок ответа, отказ только с причиной, действие по истечении срока."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import get_settings
from app.core.errors import validation
from app.core.notifications import notify
from app.core.org.models import Employee
from app.core.org.service import list_hr
from app.core.requests import service as requests
from app.core.requests.models import ESCALATED, REJECTED, SUBMITTED, Request
from app.modules.ext_guarantees.models import Policy, Reason, RequestGuarantee
from app.modules.ext_guarantees.policies import get_policy

MIN_COMMENT = 10
OTHER_REASON = "OTHER"


def fmt(dt: datetime) -> str:
    return dt.astimezone(clock.DEFAULT_TZ).strftime("%d.%m %H:%M")


async def reasons_for(session: AsyncSession, request_type: str | None) -> list[Reason]:
    rows = list(await session.scalars(select(Reason).order_by(Reason.code)))
    return [r for r in rows if request_type is None or not r.applies_to or request_type in r.applies_to]


# ---------- события движка заявок ----------


async def on_created(session: AsyncSession, request: Request, employee: Employee) -> None:
    policy = await get_policy(session, employee.country, request.type)
    if policy is None or not policy.enabled or not policy.sla_hours:
        return
    deadline = request.created_at + timedelta(hours=policy.sla_hours)
    session.add(RequestGuarantee(request_id=request.id, policy_id=policy.id, deadline_at=deadline))
    await requests.add_note(session, request, "deadline_set", {"deadlineAt": deadline.isoformat()})
    await notify(
        session,
        employee.id,
        "guarantee.deadline",
        "notif.guarantee.deadline.title",
        "notif.guarantee.deadline.body",
        {"number": request.number, "deadline": fmt(deadline)},
        {"kind": "request", "requestId": request.id},
    )


async def before_decision(
    session: AsyncSession,
    request: Request,
    decision: str,
    reason_code: str | None,
    comment: str | None,
    by_system: bool,
    overrides: dict[str, Any],
    **_: Any,
) -> None:
    """Отказ только с причиной из справочника и комментарием ≥ 10 символов — для любых типов заявок."""
    if decision != REJECTED or by_system:
        return
    if not reason_code:
        if get_settings().guarantees_require_reason:
            raise validation("REASON_REQUIRED", "Выберите причину отказа из справочника", "reasonCode")
        reason_code = overrides["reason_code"] = OTHER_REASON
    allowed = {r.code for r in await reasons_for(session, request.type)}
    if reason_code not in allowed:
        raise validation("UNKNOWN_REASON", "Такой причины нет в справочнике", "reasonCode", {"allowed": sorted(allowed)})
    if len((comment or "").strip()) < MIN_COMMENT:
        raise validation("COMMENT_REQUIRED", f"Поясните причину отказа (не меньше {MIN_COMMENT} символов)", "comment")


async def on_decided(session: AsyncSession, request: Request, **_: Any) -> None:
    g = (await session.scalars(select(RequestGuarantee).where(RequestGuarantee.request_id == request.id))).first()
    if g is not None and g.resolved_at is None:
        g.resolved_at = clock.now()


# ---------- тик: истёкшие сроки ----------


async def tick(session: AsyncSession, now: datetime) -> None:
    rows = await session.scalars(
        select(RequestGuarantee).where(RequestGuarantee.resolution == "none", RequestGuarantee.deadline_at <= now)
    )
    for g in list(rows):
        req = await session.get(Request, g.request_id)
        policy = await session.get(Policy, g.policy_id)
        if req is None or policy is None or req.status not in (SUBMITTED, ESCALATED):
            continue
        if req.status == SUBMITTED and policy.on_timeout == "auto_approve":
            await requests.decide_by_system(
                session, req.id, "Approved", "Срок ответа истёк — одобрено автоматически по политике HR", "SLA_AUTO_APPROVE"
            )
            g.resolution, g.resolved_at = "auto_approved", now
        elif req.status == SUBMITTED and req.approver_kind == "manager":
            await requests.escalate_to_hr(session, req.id, "Срок ответа руководителя истёк — заявка передана HR")
            g.resolution, g.resolved_at = "escalated", now
        else:
            # Уже адресовано HR и просрочено — отметка и напоминание HR (виден в радаре)
            await requests.add_note(session, req, "deadline_missed", {"deadlineAt": g.deadline_at.isoformat()})
            owner = await session.get(Employee, req.employee_id)
            for hr in await list_hr(session, owner.country if owner else None) or await list_hr(session):
                await notify(
                    session, hr.id, "guarantee.overdue", "notif.guarantee.overdue.title", "notif.guarantee.overdue.body",
                    {"number": req.number}, {"kind": "request", "requestId": req.id},
                )
            g.resolution = "overdue"
    await session.flush()
