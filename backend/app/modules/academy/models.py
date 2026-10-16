"""Jana Academy (CLAUDE.md §5.4). Курсы общие (country NULL) или для одной страны."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Course(Base):
    __tablename__ = "academy_courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    title_kk: Mapped[str | None] = mapped_column(String(200), default=None)
    description: Mapped[str] = mapped_column(Text)
    description_kk: Mapped[str | None] = mapped_column(Text, default=None)
    country: Mapped[str | None] = mapped_column(ForeignKey("countries.code"), default=None)
    duration_min: Mapped[int]
    passing_score: Mapped[int]  # процент
    active: Mapped[bool] = mapped_column(default=True)


class Lesson(Base):
    __tablename__ = "academy_lessons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id"), index=True)
    ord: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    content_md: Mapped[str] = mapped_column(Text)


class Question(Base):
    __tablename__ = "academy_questions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id"), index=True)
    ord: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[Any]]
    correct_index: Mapped[int]  # никогда не отдаётся в API


class Assignment(Base):
    __tablename__ = "academy_assignments"
    __table_args__ = (UniqueConstraint("employee_id", "course_id", name="uq_academy_assignment"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id"))
    assigned_by: Mapped[str] = mapped_column(ForeignKey("employees.id"))
    assigned_at: Mapped[datetime]
    due_date: Mapped[date | None] = mapped_column(default=None)


class LessonProgress(Base):
    __tablename__ = "academy_lesson_progress"

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("academy_lessons.id"), primary_key=True)
    completed_at: Mapped[datetime]


class Attempt(Base):
    __tablename__ = "academy_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id"))
    score: Mapped[int]
    passed: Mapped[bool]
    submitted_at: Mapped[datetime]
