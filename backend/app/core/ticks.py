"""Фоновый тик: раз в tick_interval_seconds вызывает обработчики модулей (гарантии, сигналы).
Демо `advance-time` вызывает тик сразу после перевода часов."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.db import sessionmaker

log = logging.getLogger("janamen.tick")

TickHandler = Callable[[AsyncSession, datetime], Awaitable[None]]


class TickRegistry:
    def __init__(self) -> None:
        self._handlers: list[tuple[str, TickHandler]] = []

    def register(self, name: str, handler: TickHandler) -> None:
        self._handlers.append((name, handler))

    def clear(self) -> None:
        self._handlers.clear()

    async def run(self, session: AsyncSession) -> list[str]:
        """Выполнить все обработчики в переданной сессии. Возвращает имена выполненных."""
        now = clock.now()
        for _name, handler in self._handlers:
            await handler(session, now)
        return [name for name, _ in self._handlers]


ticks = TickRegistry()


async def run_tick_once() -> None:
    async with sessionmaker()() as session:
        try:
            await ticks.run(session)
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("tick failed")


async def tick_loop(interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        await run_tick_once()
