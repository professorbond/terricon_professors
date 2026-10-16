"""Оргструктура: страны, подразделения, сотрудники. Источник — mock 1С:ЗУП (seed)."""

from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ROLES = ("Employee", "Manager", "HRAdmin")
UNIT_KINDS = ("sorting_center", "office", "pickup", "warehouse")


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)  # KZ, KG
    name_ru: Mapped[str] = mapped_column(String(100))
    name_kk: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3))  # KZT, KGS


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    country: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    kind: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"), default=None)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16))  # Employee | Manager | HRAdmin
    country: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    position: Mapped[str] = mapped_column(String(200))
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), default=None)
    hire_date: Mapped[date]
    qualification: Mapped[str | None] = mapped_column(String(64), default=None)
    lang: Mapped[str] = mapped_column(String(2), default="ru")
    active: Mapped[bool] = mapped_column(default=True)
