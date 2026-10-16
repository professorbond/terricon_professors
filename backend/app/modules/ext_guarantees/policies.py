"""Публичный сервис политик — его читают другие ext-модули («Зарплата по факту», радар, лестница).
Работает и при выключенном флаге guarantees: это данные, а не поведение."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ext_guarantees.models import COUNTRY_WIDE, Policy, RequestGuarantee

# Значения на случай, если политики для страны нет
DEFAULTS = {
    "wage_limit_pct": 50,
    "wage_max_per_period": 2,
    "wage_min_amount": 5000,
    "review_period_months": 12,
    "replacement_cost_pct": 30,
    "avg_annual_salary": 3_000_000,
}
MONEY_TYPES = {"wage_access"}


async def get_policy(session: AsyncSession, country: str, request_type: str) -> Policy | None:
    q = select(Policy).where(Policy.country == country, Policy.request_type == request_type)
    return (await session.scalars(q)).first()


async def setting(session: AsyncSession, country: str, request_type: str, name: str) -> int:
    policy = await get_policy(session, country, request_type)
    value = getattr(policy, name, None) if policy else None
    return int(value if value is not None else DEFAULTS[name])


async def country_setting(session: AsyncSession, country: str, name: str) -> int:
    return await setting(session, country, COUNTRY_WIDE, name)


@dataclass(frozen=True)
class GuaranteeInfo:
    deadline_at: datetime
    resolution: str


async def guarantee_for(session: AsyncSession, request_id: str) -> GuaranteeInfo | None:
    g = (await session.scalars(select(RequestGuarantee).where(RequestGuarantee.request_id == request_id))).first()
    return GuaranteeInfo(g.deadline_at, g.resolution) if g else None
