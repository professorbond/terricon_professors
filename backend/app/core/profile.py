"""Точка расширения профиля: модули добавляют свои поля в GET /api/profile/me и карточку сотрудника,
не импортируя друг друга. Отпуск даёт leaveBalance, Academy — assignedTraining, ext-фичи — своё.

    async def contribute(session, viewer, employee) -> dict[str, Any]:
        return {"leave_balance": LeaveBalance(...)}

    ctx.profile.register(contribute)
"""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.org.models import Employee
from app.core.schemas import ApiModel

# Общие схемы полей профиля, которые заполняют модули


class LeaveBalance(ApiModel):
    """days — остаток по 1С минус одобренные заявки; available — ещё минус заявки на рассмотрении."""

    days: int
    as_of: date
    pending_days: int = 0
    available_days: int


class TrainingSummary(ApiModel):
    course_id: str
    title: str
    status: str  # Assigned | InProgress | Completed
    lessons_percent: int
    score_percent: int | None
    due_date: date | None



Contributor = Callable[[AsyncSession, Employee, Employee], Awaitable[dict[str, Any]]]


class ProfileRegistry:
    def __init__(self) -> None:
        self._contributors: list[Contributor] = []

    def register(self, fn: Contributor) -> None:
        self._contributors.append(fn)

    def clear(self) -> None:
        self._contributors.clear()

    async def collect(self, session: AsyncSession, viewer: Employee, employee: Employee) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for fn in self._contributors:
            fields.update(await fn(session, viewer, employee))
        return fields


profile_registry = ProfileRegistry()
