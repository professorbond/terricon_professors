from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import conflict, validation
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.core.requests.models import APPROVED, SUBMITTED, Request
from app.integrations.zup import get_zup

TYPE = "leave"


def days_inclusive(start: date, end: date) -> int:
    """Демо-расчёт, как во фронтенде: календарные дни включительно, без праздников."""
    return (end - start).days + 1


def _period(req: Request) -> tuple[date, date]:
    return date.fromisoformat(req.payload["startDate"]), date.fromisoformat(req.payload["endDate"])


async def balance(session: AsyncSession, employee: Employee) -> tuple[int, date]:
    attrs = await get_zup().get_hr_attrs(session, employee.id)
    if attrs is None:
        return 0, clock.today()
    return attrs.vacation_days_left, attrs.vacation_as_of


async def validate_new(session: AsyncSession, employee: Employee, start: date, end: date) -> int:
    if start < clock.today():
        raise validation("START_IN_PAST", "Дата начала не может быть в прошлом", "startDate")
    if end < start:
        raise validation("END_BEFORE_START", "Дата окончания раньше даты начала", "endDate")
    days = days_inclusive(start, end)
    left, _ = await balance(session, employee)
    if days > left:
        raise validation(
            "INSUFFICIENT_BALANCE", f"Доступно {left} дн., запрошено {days}", "endDate", {"available": left}
        )
    for other in await requests.list_mine(session, employee, TYPE):
        if other.status in (SUBMITTED, APPROVED):
            o_start, o_end = _period(other)
            if start <= o_end and o_start <= end:
                raise conflict("LEAVE_OVERLAP", f"Пересекается с заявкой {other.number}", {"number": other.number})
    return days
