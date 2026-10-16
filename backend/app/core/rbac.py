"""Роли и проверки доступа. Вызываются на бэкенде в каждом эндпоинте — UI только прячет кнопки.

Матрица (CLAUDE.md, раздел 8):
  Employee — только своё;
  Manager  — своё + своя команда (прямые подчинённые), без зарплат;
  HRAdmin  — все сотрудники (просмотр), решения по заявкам, адресованным HR.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends

from app.core.auth import current_user
from app.core.errors import forbidden
from app.core.org.models import Employee

EMPLOYEE, MANAGER, HR = "Employee", "Manager", "HRAdmin"


def is_my_team(manager: Employee, employee: Employee) -> bool:
    return manager.role == MANAGER and employee.manager_id == manager.id and employee.id != manager.id


def can_view_employee(user: Employee, employee: Employee) -> bool:
    return user.id == employee.id or user.role == HR or is_my_team(user, employee)


def can_view_salary(user: Employee, employee: Employee) -> bool:
    """Зарплаты конкретных людей: только своя или HR."""
    return user.id == employee.id or user.role == HR


def ensure(condition: bool, message: str = "Недостаточно прав") -> None:
    if not condition:
        raise forbidden(message)


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, Employee]]:
    """FastAPI-зависимость: `user: Employee = Depends(require_role(HR))`."""

    async def dep(user: Employee = Depends(current_user)) -> Employee:
        if user.role not in roles:
            raise forbidden()
        return user

    return dep
