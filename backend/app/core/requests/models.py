from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Статусы совпадают с фронтендом (LeaveStatus) + Escalated (передано HR по сроку)
SUBMITTED, APPROVED, REJECTED, ESCALATED, CANCELLED = "Submitted", "Approved", "Rejected", "Escalated", "Cancelled"
OPEN_STATUSES = (SUBMITTED, ESCALATED)


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (UniqueConstraint("employee_id", "submission_key", name="uq_requests_submission"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    approver_kind: Mapped[str] = mapped_column(String(16))  # manager | hr | none
    approver_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None, index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    payload: Mapped[dict[str, Any]]
    submission_key: Mapped[str | None] = mapped_column(String(64), default=None)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime]
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None)
    decided_by_system: Mapped[bool] = mapped_column(default=False)
    decision_reason_code: Mapped[str | None] = mapped_column(String(64), default=None)
    decision_comment: Mapped[str | None] = mapped_column(Text, default=None)

    events: Mapped[list["RequestEvent"]] = relationship(
        back_populates="request", order_by="RequestEvent.at", cascade="all, delete-orphan", lazy="selectin"
    )


class RequestEvent(Base):
    __tablename__ = "request_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime]
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None)
    actor_kind: Mapped[str] = mapped_column(String(8))  # user | system
    # created | approved | rejected | escalated | cancelled | note (произвольная отметка модуля)
    event: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))  # статус заявки после события
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    data: Mapped[dict[str, Any]]

    request: Mapped[Request] = relationship(back_populates="events")


class RequestCounter(Base):
    """Счётчик видимых номеров (JL-2026-0001) — атомарно через upsert, без гонок."""

    __tablename__ = "request_counters"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)  # "JL-2026"
    value: Mapped[int]
