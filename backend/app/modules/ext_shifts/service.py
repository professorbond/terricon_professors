"""Правила биржи смен: тот же центр, та же квалификация, не в прошлом, без пересечений."""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import AppError, conflict, forbidden, not_found, validation
from app.core.ids import new_id
from app.core.notifications import notify
from app.core.org.models import Employee, Unit
from app.integrations.zup import get_zup
from app.modules.ext_shifts.models import Shift, ShiftEvent

ACTIVE = ("assigned", "offered", "taken")  # смена за кем-то закреплена


async def center_of(session: AsyncSession, unit_id: str) -> str:
    unit = await session.get(Unit, unit_id)
    while unit is not None and unit.parent_id:
        unit = await session.get(Unit, unit.parent_id)
    return unit.id if unit else unit_id


def interval(s: Shift) -> tuple[datetime, datetime]:
    start = datetime.combine(s.date, time.fromisoformat(s.start_time), clock.DEFAULT_TZ)
    end = datetime.combine(s.date, time.fromisoformat(s.end_time), clock.DEFAULT_TZ)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def overlaps(a: Shift, b: Shift) -> bool:
    (a1, a2), (b1, b2) = interval(a), interval(b)
    return a1 < b2 and b1 < a2


async def my_shifts(session: AsyncSession, emp: Employee, from_date: date | None = None) -> list[Shift]:
    q = select(Shift).where(Shift.assignee_id == emp.id, Shift.status.in_(ACTIVE), Shift.date >= (from_date or clock.today()))
    return list(await session.scalars(q.order_by(Shift.date, Shift.start_time)))


async def pay_for(session: AsyncSession, emp: Employee, s: Shift) -> int | None:
    salary = await get_zup().get_salary(session, emp.id)
    if salary and salary.shift_rate:
        return salary.shift_rate
    return s.pay_preview


def _event(session: AsyncSession, s: Shift, event: str, actor: Employee | None, **data: object) -> None:
    session.add(ShiftEvent(id=new_id(), shift_id=s.id, at=clock.now(), actor_id=actor.id if actor else None, event=event, data=dict(data)))


async def check_can_take(session: AsyncSession, emp: Employee, s: Shift) -> None:
    if s.status not in ("offered", "open"):
        raise conflict("SHIFT_NOT_AVAILABLE", "Смену уже взяли или она не выставлена")
    if s.assignee_id == emp.id:
        raise validation("SHIFT_NOT_AVAILABLE", "Это ваша смена")
    if s.center_id != await center_of(session, emp.unit_id):
        raise forbidden("Смена в другом центре")
    if s.qualification != emp.qualification:
        raise validation("QUALIFICATION_MISMATCH", f"Нужна квалификация «{s.qualification}»", data={"required": s.qualification})
    if interval(s)[0] <= clock.now():
        raise validation("SHIFT_IN_PAST", "Смена уже началась или прошла")
    for mine in await my_shifts(session, emp, s.date - timedelta(days=1)):
        if overlaps(mine, s):
            raise validation("SHIFT_OVERLAP", f"Пересекается с вашей сменой {mine.date:%d.%m} {mine.start_time}–{mine.end_time}", data={"shiftId": mine.id})


async def lock(session: AsyncSession, shift_id: str) -> Shift:
    q = select(Shift).where(Shift.id == shift_id).with_for_update().execution_options(populate_existing=True)
    s = (await session.scalars(q)).first()
    if s is None:
        raise not_found("Смена не найдена")
    return s


async def offer(session: AsyncSession, emp: Employee, shift_id: str) -> Shift:
    s = await lock(session, shift_id)
    if s.assignee_id != emp.id:
        raise forbidden("Отдать можно только свою смену")
    if s.status not in ("assigned", "taken"):
        raise conflict("SHIFT_NOT_AVAILABLE", "Смена уже выставлена")
    if interval(s)[0] <= clock.now():
        raise validation("SHIFT_IN_PAST", "Смена уже началась или прошла")
    s.status, s.version = "offered", s.version + 1
    _event(session, s, "offered", emp)
    await session.flush()
    return s


async def cancel_offer(session: AsyncSession, emp: Employee, shift_id: str) -> Shift:
    s = await lock(session, shift_id)
    if s.assignee_id != emp.id or s.status != "offered":
        raise conflict("SHIFT_NOT_AVAILABLE", "Смену уже взяли или она не выставлена")
    s.status, s.version = "assigned", s.version + 1
    _event(session, s, "offer_cancelled", emp)
    await session.flush()
    return s


async def take(session: AsyncSession, emp: Employee, shift_id: str) -> tuple[Shift, int | None]:
    s = await lock(session, shift_id)
    await check_can_take(session, emp, s)
    previous = s.assignee_id
    pay = await pay_for(session, emp, s)
    s.assignee_id, s.status, s.version = emp.id, "taken", s.version + 1
    _event(session, s, "taken", emp, previousAssignee=previous)
    when = f"{s.date:%d.%m} {s.start_time}–{s.end_time}"
    await notify(session, emp.id, "shift.taken", "notif.shift.taken.title", "notif.shift.taken.body", {"when": when, "pay": pay or 0})
    if previous:
        await notify(
            session, previous, "shift.given", "notif.shift.given.title", "notif.shift.given.body", {"when": when, "name": emp.full_name}
        )
    await session.flush()
    return s, pay


async def publish_open(
    session: AsyncSession, actor: Employee, day: date, start: str, end: str, qualification: str, pay_preview: int, center_id: str
) -> Shift:
    if day < clock.today():
        raise validation("SHIFT_IN_PAST", "Нельзя публиковать смену в прошлом", "date")
    try:
        time.fromisoformat(start), time.fromisoformat(end)
    except ValueError:
        raise AppError("validation", "INVALID_TIME", "Время в формате ЧЧ:ММ", {"startTime": ["ЧЧ:ММ"]}) from None
    s = Shift(
        id=new_id(), center_id=center_id, date=day, start_time=start, end_time=end,
        qualification=qualification, status="open", pay_preview=pay_preview, published_by=actor.id,
    )
    session.add(s)
    _event(session, s, "published", actor, payPreview=pay_preview)
    await session.flush()
    return s
