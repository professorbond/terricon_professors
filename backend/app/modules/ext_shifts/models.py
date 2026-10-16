from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Shift(Base):
    """Смена в центре (CLAUDE.md §7.8). center_id — корневое подразделение (сортировочный центр/склад)."""

    __tablename__ = "ext_shifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    center_id: Mapped[str] = mapped_column(ForeignKey("units.id"), index=True)
    date: Mapped[date]
    start_time: Mapped[str] = mapped_column(String(5))  # 08:00
    end_time: Mapped[str] = mapped_column(String(5))  # 20:00 (меньше начала — смена через полночь)
    qualification: Mapped[str] = mapped_column(String(64))
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None, index=True)
    status: Mapped[str] = mapped_column(String(16))  # assigned | offered | open | taken
    pay_preview: Mapped[int | None] = mapped_column(default=None)
    published_by: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None)
    version: Mapped[int] = mapped_column(default=1)


class ShiftEvent(Base):
    __tablename__ = "ext_shift_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    shift_id: Mapped[str] = mapped_column(ForeignKey("ext_shifts.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime]
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None)
    event: Mapped[str] = mapped_column(String(32))  # published | assigned | offered | offer_cancelled | taken
    data: Mapped[dict[str, Any]]
