from datetime import date, datetime
from typing import Any

from app.core.schemas import ApiModel


class SignalOut(ApiModel):
    id: str
    kind: str
    title: str  # причина человеческим языком
    details: dict[str, Any]
    detected_at: datetime
    status: str
    action: str | None
    actioned_at: datetime | None
    retained_confirmed: bool


class RiskCard(ApiModel):
    employee_id: str
    employee_name: str
    position: str
    department: str
    country: str
    manager_name: str | None
    open_signals: int
    signals: list[SignalOut]
    next_review_date: date | None


class SavingsOut(ApiModel):
    """«Радар сохранил 12 сотрудников = 10,8 млн ₸»."""

    country: str
    currency: str
    retained_count: int
    per_person: int  # avg_annual_salary × replacement_cost_pct / 100
    saved: int
    formula: str
