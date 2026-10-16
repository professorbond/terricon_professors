from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import conflict, validation
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.core.requests.models import APPROVED, SUBMITTED, Request
from app.integrations.zup import get_zup

TYPE = "vacation"


def days_inclusive(start: date, end: date) -> int:
    """Демо-расчёт, как во фронтенде: календарные дни включительно, без праздников."""
    return (end - start).days + 1


def period(req: Request) -> tuple[date, date]:
    return date.fromisoformat(req.payload["startDate"]), date.fromisoformat(req.payload["endDate"])


async def balance(session: AsyncSession, employee: Employee) -> dict:
    """Остаток считается поверх 1С:ЗУП, в 1С ничего не пишется.
    days = остаток 1С на дату as_of − одобренные отпуска после неё; available = days − на рассмотрении."""
    attrs = await get_zup().get_hr_attrs(session, employee.id)
    if attrs is None:
        return {"days": 0, "as_of": clock.today(), "pending_days": 0, "available_days": 0}
    approved = pending = 0
    for req in await requests.list_mine(session, employee, TYPE):
        start, _ = period(req)
        if start < attrs.vacation_as_of:
            continue
        if req.status == APPROVED:
            approved += req.payload["requestedDays"]
        elif req.status == SUBMITTED:
            pending += req.payload["requestedDays"]
    days = attrs.vacation_days_left - approved
    return {"days": days, "as_of": attrs.vacation_as_of, "pending_days": pending, "available_days": days - pending}


async def validate_new(session: AsyncSession, employee: Employee, start: date, end: date) -> int:
    if start < clock.today():
        raise validation("INVALID_DATES", "Дата начала не может быть в прошлом", "startDate")
    if end < start:
        raise validation("INVALID_DATES", "Дата окончания раньше даты начала", "endDate")
    days = days_inclusive(start, end)
    available = (await balance(session, employee))["available_days"]
    if days > available:
        raise validation(
            "INSUFFICIENT_BALANCE", f"Доступно {available} дн., запрошено {days}", "endDate", {"available": available}
        )
    for other in await requests.list_mine(session, employee, TYPE):
        if other.status in (SUBMITTED, APPROVED):
            o_start, o_end = period(other)
            if start <= o_end and o_start <= end:
                raise conflict("OVERLAP", f"Пересекается с заявкой {other.number}", {"number": other.number})
    return days
