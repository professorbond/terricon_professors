from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.requests.schemas import DocumentRef, RequestPermissions
from app.core.schemas import ApiModel


class SubmitLeaveIn(ApiModel):
    """Совпадает с SubmitLeaveInput фронтенда."""

    submission_key: str = Field(min_length=1, max_length=64)
    start_date: date
    end_date: date
    comment: str = Field(default="", max_length=1000)


class LeaveDecisionIn(ApiModel):
    """Совпадает с LeaveDecision фронтенда (+ reasonCode для справочника причин)."""

    decision: Literal["Approved", "Rejected"]
    expected_version: int
    comment: str | None = None
    reason_code: str | None = None


class LeaveEventOut(ApiModel):
    id: str
    status: str
    occurred_at: datetime
    actor_label: str
    actor_id: str  # "system" для системных событий (у фронтенда тип string)
    comment: str | None
    event: str


class LeaveRequestOut(ApiModel):
    """Совпадает с LeaveRequest фронтенда (+ decision*, permissions)."""

    id: str
    number: str
    type: Literal["Leave"] = "Leave"
    submission_key: str
    employee_id: str
    employee_name: str
    manager_id: str
    manager_name: str
    start_date: date
    end_date: date
    requested_days: int
    comment: str
    status: str
    created_at: datetime
    version: int
    history: list[LeaveEventOut]
    decision_comment: str | None
    decision_reason_code: str | None
    decided_by_system: bool
    documents: list[DocumentRef]
    permissions: RequestPermissions


class LeaveBalanceOut(ApiModel):
    days: int
    as_of: date
    pending_days: int
    available_days: int
