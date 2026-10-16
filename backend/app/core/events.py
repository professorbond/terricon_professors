"""Шина событий в процессе. Модули подписываются на события каркаса и друг друга,
не импортируя внутренности чужих модулей.

Обработчики вызываются последовательно в той же транзакции (session передаётся в payload).
Обработчик `request.before_decision` может запретить решение, бросив AppError.

События каркаса:
  request.created          {session, request, employee}
  request.before_decision  {session, request, actor, decision, reason_code, comment, by_system}
  request.decided          {session, request, actor, by_system}
  request.cancelled        {session, request, actor}
"""

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[..., Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event: str) -> Callable[[Handler], Handler]:
        def decorator(fn: Handler) -> Handler:
            self._handlers[event].append(fn)
            return fn

        return decorator

    def subscribe(self, event: str, fn: Handler) -> None:
        self._handlers[event].append(fn)

    def clear(self) -> None:
        self._handlers.clear()

    async def emit(self, event: str, **payload: Any) -> None:
        for handler in list(self._handlers[event]):
            await handler(**payload)


events = EventBus()
