from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import forbidden, not_found, validation
from app.core.i18n import t
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.core.requests.models import OPEN_STATUSES, REJECTED
from app.core.requests.registry import request_types
from app.integrations.zup import get_zup
from app.modules.ext_guarantees import service
from app.modules.ext_guarantees.models import Policy, RequestGuarantee
from app.modules.ext_guarantees.policies import MONEY_TYPES, country_setting
from app.modules.ext_guarantees.schemas import OpenGuarantee, PolicyOut, PolicyUpdate, ReasonOut, SummaryOut

router = APIRouter(prefix="/api/ext", tags=["ext: guarantees"])


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    return date(d.year + month // 12, month % 12 + 1, min(d.day, 28))


async def next_salary_review(session: AsyncSession, employee: Employee) -> date | None:
    attrs = await get_zup().get_hr_attrs(session, employee.id)
    if attrs is None or attrs.last_salary_review_date is None:
        return None
    return add_months(attrs.last_salary_review_date, await country_setting(session, employee.country, "review_period_months"))


@router.get("/guarantees/summary/me", response_model=SummaryOut, response_model_by_alias=True)
async def summary(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """«Мои гарантии»: сроки по открытым заявкам, отказы без причины, ответы в срок, пересмотр ЗП."""
    open_items, on_time, total, without_reason = [], 0, 0, 0
    for req in await requests.list_mine(session, user):
        g = (await session.scalars(select(RequestGuarantee).where(RequestGuarantee.request_id == req.id))).first()
        if req.status in OPEN_STATUSES and g is not None:
            open_items.append(
                OpenGuarantee(
                    request_id=req.id, number=req.number, type=req.type,
                    type_title=t(request_types.get(req.type).title_key, user.lang), deadline_at=g.deadline_at,
                )
            )
        if req.decided_at is not None and g is not None:
            total += 1
            on_time += int(req.decided_at <= g.deadline_at or g.resolution == "auto_approved")
        if req.status == REJECTED and not req.decision_reason_code:
            without_reason += 1
    return SummaryOut(
        open_requests=open_items,
        rejections_without_reason=without_reason,
        decided_on_time=on_time,
        decided_total=total,
        next_salary_review=await next_salary_review(session, user),
    )


@router.get("/guarantees/reasons", response_model=list[ReasonOut], response_model_by_alias=True)
async def reasons(type: str | None = None, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Справочник причин отказа (для окна решения по заявке)."""
    return [ReasonOut(code=r.code, title=t(r.title_key, user.lang)) for r in await service.reasons_for(session, type)]


def policy_out(p: Policy) -> PolicyOut:
    return PolicyOut.model_validate(p, from_attributes=True)


@router.get("/policies", response_model=list[PolicyOut], response_model_by_alias=True)
async def list_policies(country: str | None = None, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Политики читают все (своя страна); HR — любую страну."""
    country = country or user.country
    if country != user.country and user.role != rbac.HR:
        raise forbidden("Политики другой страны доступны только HR")
    rows = await session.scalars(select(Policy).where(Policy.country == country).order_by(Policy.request_type))
    return [policy_out(p) for p in rows]


@router.put("/policies/{policy_id}", response_model=PolicyOut, response_model_by_alias=True)
async def update_policy(
    policy_id: int, body: PolicyUpdate, user: Employee = Depends(rbac.require_role(rbac.HR)), session: AsyncSession = DbSession
):
    policy = await session.get(Policy, policy_id)
    if policy is None:
        raise not_found("Политика не найдена")
    changes = body.model_dump(exclude_unset=True)
    on_timeout = changes.get("on_timeout", policy.on_timeout)
    if policy.request_type in MONEY_TYPES and on_timeout == "auto_approve":
        raise validation("AUTO_APPROVE_FORBIDDEN", "Для денежных заявок автоодобрение по сроку запрещено", "onTimeout")
    for key, value in changes.items():
        setattr(policy, key, value)
    policy.updated_by, policy.updated_at = user.id, clock.now()
    return policy_out(policy)
