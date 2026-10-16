"""Радар удержания (CLAUDE.md §7.5) и пересмотры зарплаты.

ext_salary_reviews создаёт радар («Предложить пересмотр»), читает лестница (дата следующего пересмотра)."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RiskSignal(Base):
    __tablename__ = "ext_risk_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # no_review | rejections | pay_equity | slow_answers | open_grievance
    details: Mapped[dict[str, Any]]
    detected_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | actioned | resolved
    action: Mapped[str | None] = mapped_column(String(32), default=None)
    actioned_at: Mapped[datetime | None] = mapped_column(default=None)
    retained_confirmed: Mapped[bool] = mapped_column(default=False)


class SalaryReview(Base):
    __tablename__ = "ext_salary_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    proposed_by: Mapped[str] = mapped_column(ForeignKey("employees.id"))
    proposed_at: Mapped[datetime]
    review_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(16), default="proposed")  # proposed | done
    source_signal_id: Mapped[str | None] = mapped_column(ForeignKey("ext_risk_signals.id"), default=None)
