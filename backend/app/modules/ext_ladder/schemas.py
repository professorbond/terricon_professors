from datetime import date
from typing import Literal

from app.core.schemas import ApiModel


class GradeOut(ApiModel):
    code: str
    title: str
    band_min: int
    band_max: int
    currency: str


class Criterion(ApiModel):
    kind: Literal["course", "months_in_grade", "no_incidents"]
    title: str
    done: bool
    course_id: str | None = None
    required: int | None = None
    actual: int | None = None


class LadderOut(ApiModel):
    """«Сейчас: Сортировщик · 230–270 тыс ₸ → Дальше: Старший сортировщик · 275–320 тыс ₸»."""

    current: GradeOut | None
    next: GradeOut | None
    criteria: list[Criterion]
    criteria_done: int
    criteria_total: int
    remaining_courses: int
    raise_to_next_min: int | None  # «+35 000 ₸ к нижней границе» — от собственного оклада
    next_review_date: date | None
    ready: bool


class CourseTag(ApiModel):
    course_id: str
    grades: list[GradeOut]  # «Нужен для грейда SORT-2»
