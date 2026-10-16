from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.db import Base
from app.core.demo.models import DemoState


async def load_offset(session: AsyncSession) -> None:
    state = await session.get(DemoState, 1)
    clock.set_offset(timedelta(seconds=state.offset_seconds if state else 0))


async def save_offset(session: AsyncSession, offset: timedelta) -> None:
    state = await session.get(DemoState, 1)
    if state is None:
        state = DemoState(id=1, offset_seconds=0)
        session.add(state)
    state.offset_seconds = int(offset.total_seconds())
    clock.set_offset(offset)
    await session.flush()


async def wipe_all(session: AsyncSession) -> None:
    """Удалить все данные (структура таблиц и версия миграций остаются)."""
    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(delete(table))
    clock.set_offset(timedelta(0))
    await session.flush()
