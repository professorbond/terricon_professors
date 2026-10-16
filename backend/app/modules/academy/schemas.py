"""Схемы Academy. CourseSummary и CourseProgress совпадают с моделями фронтенда (features/academy/model.ts)."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.schemas import ApiModel

CourseStatus = Literal["Assigned", "InProgress", "Completed"]


class CourseProgress(ApiModel):
    course_id: str
    completed_lesson_ids: list[str]
    total_lessons: int
    status: CourseStatus
    score_percent: int | None
    # Расширение: тест сдан, процент уроков
    passed: bool = False
    lessons_percent: int = 0


class CourseSummary(ApiModel):
    id: str
    title: str
    description: str
    duration_minutes: int


class AssignedCourse(CourseSummary):
    assigned_at: datetime
    due_date: date | None
    progress: CourseProgress


class LessonOut(ApiModel):
    id: str
    ord: int
    title: str
    content_md: str
    completed: bool


class QuestionOut(ApiModel):
    """Вопрос теста — без правильного ответа."""

    id: str
    ord: int
    text: str
    options: list[str]


class CourseDetail(CourseSummary):
    passing_score: int
    assigned: bool
    lessons: list[LessonOut]
    questions: list[QuestionOut]
    progress: CourseProgress | None


class SubmitIn(ApiModel):
    answers: list[int] = Field(description="Индекс выбранного варианта для каждого вопроса по порядку")


class SubmitOut(ApiModel):
    score: int
    passed: bool
    passing_score: int
    correct: int
    total: int
    progress: CourseProgress


class AssignIn(ApiModel):
    employee_id: str
    course_id: str
    due_date: date | None = None


class AssignmentOut(ApiModel):
    id: str
    employee_id: str
    course_id: str
    assigned_by: str
    assigned_at: datetime
    due_date: date | None


class ProgressRow(ApiModel):
    employee_id: str
    employee_name: str
    unit_id: str
    course_id: str
    course_title: str
    due_date: date | None
    progress: CourseProgress
