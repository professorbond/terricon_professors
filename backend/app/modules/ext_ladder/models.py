from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GradeLadder(Base):
    """Грейд, вилка и условия перехода на следующий (CLAUDE.md §7.4). Зарплат конкретных людей здесь нет."""

    __tablename__ = "ext_grade_ladders"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    country: Mapped[str] = mapped_column(ForeignKey("countries.code"), index=True)
    title_key: Mapped[str] = mapped_column(String(64))
    band_min: Mapped[int]
    band_max: Mapped[int]
    next_grade_code: Mapped[str | None] = mapped_column(String(32), default=None)
    required_course_ids: Mapped[list[Any]]
    min_months_in_grade: Mapped[int] = mapped_column(default=0)
    min_months_no_incidents: Mapped[int] = mapped_column(default=0)
