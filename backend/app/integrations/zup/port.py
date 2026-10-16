from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class Salary:
    monthly_base: int
    shift_rate: int | None
    night_bonus_rate: int | None


@dataclass(frozen=True)
class TimesheetEntry:
    date: date
    hours: int
    shift_type: str


@dataclass(frozen=True)
class HrAttrs:
    grade_code: str
    last_salary_review_date: date | None
    vacation_days_left: int
    vacation_as_of: date
    incidents_last_date: date | None
    planned_shifts_per_month: int


@dataclass(frozen=True)
class HireOffer:
    id: str
    position: str
    grade_code: str
    country: str
    offered_monthly_base: int
    offered_at: datetime


class ZupPort(Protocol):
    """Контракт чтения из 1С:ЗУП. Методов записи нет намеренно: изменения — документом."""

    async def get_salary(self, session: AsyncSession, employee_id: str) -> Salary | None: ...

    async def get_timesheet(
        self, session: AsyncSession, employee_id: str, start: date, end: date
    ) -> list[TimesheetEntry]: ...

    async def get_hr_attrs(self, session: AsyncSession, employee_id: str) -> HrAttrs | None: ...

    async def list_recent_offers(self, session: AsyncSession, since: datetime) -> list[HireOffer]: ...
