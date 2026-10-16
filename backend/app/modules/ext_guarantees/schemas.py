from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.schemas import ApiModel


class GuaranteeBadge(ApiModel):
    """Для бейджа в карточке заявки: «Ответ до 18 окт» / «Одобрено по сроку» / «Передано HR»."""

    deadline_at: datetime
    resolution: Literal["none", "auto_approved", "escalated", "overdue"]
    overdue: bool  # срок истёк, а решения нет
    decided_late: bool  # решение принято позже срока


class ReasonOut(ApiModel):
    code: str
    title: str


class OpenGuarantee(ApiModel):
    request_id: str
    number: str
    type: str
    type_title: str
    deadline_at: datetime


class SummaryOut(ApiModel):
    """Блок «Мои гарантии» на главной."""

    open_requests: list[OpenGuarantee]
    rejections_without_reason: int
    decided_on_time: int
    decided_total: int
    next_salary_review: date | None


class PolicyOut(ApiModel):
    id: int
    country: str
    request_type: str
    sla_hours: int | None
    on_timeout: str | None
    enabled: bool
    wage_limit_pct: int | None
    wage_max_per_period: int | None
    wage_min_amount: int | None
    review_period_months: int | None
    replacement_cost_pct: int | None
    avg_annual_salary: int | None
    updated_at: datetime


class PolicyUpdate(ApiModel):
    sla_hours: int | None = Field(default=None, ge=1, le=24 * 30)
    on_timeout: Literal["auto_approve", "escalate_hr"] | None = None
    enabled: bool | None = None
    wage_limit_pct: int | None = Field(default=None, ge=0, le=100)
    wage_max_per_period: int | None = Field(default=None, ge=0, le=31)
    wage_min_amount: int | None = Field(default=None, ge=0)
    review_period_months: int | None = Field(default=None, ge=1, le=60)
    replacement_cost_pct: int | None = Field(default=None, ge=0, le=300)
    avg_annual_salary: int | None = Field(default=None, ge=0)
