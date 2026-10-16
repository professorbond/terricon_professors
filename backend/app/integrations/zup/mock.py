from dataclasses import replace
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.documentolog.models import Document
from app.integrations.zup.models import ZupHireOffer, ZupHrAttrs, ZupSalary, ZupTimesheet
from app.integrations.zup.port import HireOffer, HrAttrs, Salary, TimesheetEntry


class MockZup:
    """Читает таблицы zup_*. Остаток отпуска учитывает приказы, «проведённые» в 1С через
    Documentolog (документы leave_order) — так же, как это сделает настоящий 1С."""

    async def get_salary(self, session: AsyncSession, employee_id: str) -> Salary | None:
        row = await session.get(ZupSalary, employee_id)
        if row is None:
            return None
        return Salary(row.monthly_base, row.shift_rate, row.night_bonus_rate)

    async def get_timesheet(
        self, session: AsyncSession, employee_id: str, start: date, end: date
    ) -> list[TimesheetEntry]:
        rows = await session.scalars(
            select(ZupTimesheet)
            .where(ZupTimesheet.employee_id == employee_id, ZupTimesheet.date >= start, ZupTimesheet.date <= end)
            .order_by(ZupTimesheet.date)
        )
        return [TimesheetEntry(r.date, r.hours, r.shift_type) for r in rows]

    async def get_hr_attrs(self, session: AsyncSession, employee_id: str) -> HrAttrs | None:
        row = await session.get(ZupHrAttrs, employee_id)
        if row is None:
            return None
        attrs = HrAttrs(
            row.grade_code,
            row.last_salary_review_date,
            row.vacation_days_left,
            row.vacation_as_of,
            row.incidents_last_date,
            row.planned_shifts_per_month,
        )
        orders = await session.scalars(
            select(Document).where(
                Document.employee_id == employee_id, Document.kind == "leave_order", Document.status == "registered"
            )
        )
        used = sum(int(d.data.get("days", 0)) for d in orders)
        return replace(attrs, vacation_days_left=attrs.vacation_days_left - used)

    async def list_recent_offers(self, session: AsyncSession, since: datetime) -> list[HireOffer]:
        rows = await session.scalars(select(ZupHireOffer).where(ZupHireOffer.offered_at >= since))
        return [
            HireOffer(r.id, r.position, r.grade_code, r.country, r.offered_monthly_base, r.offered_at) for r in rows
        ]
