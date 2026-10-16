"""Публичный сервис радара для других модулей (рентген): кто из сотрудников сейчас в зоне риска."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ext_hr_console.models import RiskSignal


async def employees_at_risk(session: AsyncSession, employee_ids: list[str]) -> set[str]:
    if not employee_ids:
        return set()
    q = select(RiskSignal.employee_id).where(RiskSignal.employee_id.in_(employee_ids), RiskSignal.status == "open")
    return set(await session.scalars(q))
