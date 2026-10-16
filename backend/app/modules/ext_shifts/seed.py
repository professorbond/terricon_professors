"""Ближайшие смены СЦ Алматы и склада Бишкек + открытая смена на пик (CLAUDE.md §12, п. 9)."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.modules.ext_shifts.models import Shift
from app.seed.loader import emp_id

ALMATY, BISHKEK = "kz-almaty-sc", "kg-bishkek-wh"
# (логин, центр, смещения дней, начало, конец)
PLAN = [
    ("aigerim", ALMATY, (1, 3, 5), "08:00", "20:00"),
    ("asel", ALMATY, (2, 4, 6), "08:00", "20:00"),  # свободна в дни смен Айгерим
    ("nurlan", ALMATY, (1, 4), "20:00", "08:00"),
    ("bakyt", BISHKEK, (1, 2, 4), "09:00", "21:00"),
]


async def seed(session: AsyncSession) -> None:
    today = clock.today()
    for login, center, days, start, end in PLAN:
        for d in days:
            session.add(Shift(
                id=new_id(), center_id=center, date=today + timedelta(days=d), start_time=start, end_time=end,
                qualification="sorter", assignee_id=emp_id(login), status="assigned",
            ))
    # Пик распродаж: открытая смена от руководителя смены Б
    session.add(Shift(
        id=new_id(), center_id=ALMATY, date=today + timedelta(days=7), start_time="08:00", end_time="20:00",
        qualification="sorter", status="open", pay_preview=12000, published_by=emp_id("erlan"),
    ))
    await session.flush()
