"""Публичный сервис для лестницы: последний предложенный пересмотр зарплаты."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ext_hr_console.models import SalaryReview


async def proposed_review_date(session: AsyncSession, employee_id: str) -> date | None:
    q = (
        select(SalaryReview.review_date)
        .where(SalaryReview.employee_id == employee_id, SalaryReview.status == "proposed")
        .order_by(SalaryReview.proposed_at.desc())
    )
    return (await session.scalars(q)).first()
