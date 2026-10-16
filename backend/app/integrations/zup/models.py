"""Таблицы-зеркало 1С:ЗУП для mock. Пишет в них только seed. Приложение их только читает."""

from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ZupSalary(Base):
    __tablename__ = "zup_salaries"

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    monthly_base: Mapped[int]  # тенге/сом, целые
    shift_rate: Mapped[int | None] = mapped_column(default=None)
    night_bonus_rate: Mapped[int | None] = mapped_column(default=None)


class ZupTimesheet(Base):
    __tablename__ = "zup_timesheets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date]
    hours: Mapped[int]
    shift_type: Mapped[str] = mapped_column(String(16))  # day | night


class ZupHrAttrs(Base):
    __tablename__ = "zup_hr_attrs"

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    grade_code: Mapped[str] = mapped_column(String(32))
    last_salary_review_date: Mapped[date | None] = mapped_column(default=None)
    vacation_days_left: Mapped[int]
    vacation_as_of: Mapped[date]
    incidents_last_date: Mapped[date | None] = mapped_column(default=None)
    planned_shifts_per_month: Mapped[int] = mapped_column(default=22)


class ZupHireOffer(Base):
    __tablename__ = "zup_hire_offers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    position: Mapped[str] = mapped_column(String(200))
    grade_code: Mapped[str] = mapped_column(String(32))
    country: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    offered_monthly_base: Mapped[int]
    offered_at: Mapped[datetime]
