"""Гарантии и политики HR (CLAUDE.md §7.1). Политики — по стране и типу заявки;
строка request_type="*" — настройки страны (пересмотр, стоимость замены)."""

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

COUNTRY_WIDE = "*"


class Policy(Base):
    __tablename__ = "ext_policies"
    __table_args__ = (UniqueConstraint("country", "request_type", name="uq_ext_policy"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    request_type: Mapped[str] = mapped_column(String(32))
    sla_hours: Mapped[int | None] = mapped_column(default=None)
    on_timeout: Mapped[str | None] = mapped_column(String(16), default=None)  # auto_approve | escalate_hr
    enabled: Mapped[bool] = mapped_column(default=True)
    wage_limit_pct: Mapped[int | None] = mapped_column(default=None)
    wage_max_per_period: Mapped[int | None] = mapped_column(default=None)
    wage_min_amount: Mapped[int | None] = mapped_column(default=None)
    review_period_months: Mapped[int | None] = mapped_column(default=None)
    replacement_cost_pct: Mapped[int | None] = mapped_column(default=None)
    avg_annual_salary: Mapped[int | None] = mapped_column(default=None)
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None)
    updated_at: Mapped[datetime]


class Reason(Base):
    __tablename__ = "ext_reasons"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title_key: Mapped[str] = mapped_column(String(64))
    applies_to: Mapped[list[Any]]  # типы заявок; [] — любые


class RequestGuarantee(Base):
    __tablename__ = "ext_request_guarantees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), unique=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("ext_policies.id"))
    deadline_at: Mapped[datetime]
    # none | auto_approved | escalated | overdue (истёк у заявки, уже адресованной HR)
    resolution: Mapped[str] = mapped_column(String(16), default="none")
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)
