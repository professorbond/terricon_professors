from datetime import date

from app.core.profile import LeaveBalance, TrainingSummary
from app.core.schemas import ApiModel


class PersonRef(ApiModel):
    id: str
    display_name: str


class EmployeeProfile(ApiModel):
    """Совпадает с EmployeeProfile фронтенда + расширения (CLAUDE.md §5.1)."""

    id: str
    display_name: str
    company: str
    position: str
    department: str
    manager: PersonRef | None
    hired_on: date
    leave_balance: LeaveBalance | None = None
    role: str
    country: str
    lang: str
    unit_id: str
    unit_kind: str | None
    qualification: str | None
    grade_code: str | None
    # Только сам сотрудник и HR (rbac.can_view_salary), остальным null
    monthly_base: int | None = None
    assigned_training: list[TrainingSummary] = []
    # Только в собственном профиле
    unread_notifications: int | None = None
