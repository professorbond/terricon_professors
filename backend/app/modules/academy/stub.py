"""ЗАГЛУШКА этапа 1: фиксированные ответы в финальном формате, чтобы фронтенд верстал параллельно.
Заменяется настоящей реализацией на этапе 2. Ответы помечены заголовком X-Stub: true."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Response

from app.core.auth import current_user
from app.core.org.models import Employee
from app.core.schemas import Page
from app.modules.academy.schemas import (
    AssignedCourse,
    AssignIn,
    AssignmentOut,
    CourseDetail,
    CourseProgress,
    CourseSummary,
    LessonOut,
    ProgressRow,
    QuestionOut,
    SubmitIn,
    SubmitOut,
)

router = APIRouter(prefix="/api/academy", tags=["academy (stub)"])

C1, C2 = "course-returns", "course-safety"
SUMMARIES = [
    CourseSummary(id=C1, title="Работа с возвратами", description="Приём, проверка и оформление возвратов на сортировке", duration_minutes=40),
    CourseSummary(id=C2, title="Техника безопасности на сортировке", description="Правила безопасной работы с конвейером и грузами", duration_minutes=30),
]
P1 = CourseProgress(course_id=C1, completed_lesson_ids=["l-ret-1", "l-ret-2", "l-ret-3"], total_lessons=3, status="Completed", score_percent=100, passed=True, lessons_percent=100)
P2 = CourseProgress(course_id=C2, completed_lesson_ids=["l-saf-1"], total_lessons=3, status="InProgress", score_percent=None, passed=False, lessons_percent=33)


def _stub(response: Response) -> None:
    response.headers["X-Stub"] = "true"


@router.get("/courses", response_model=Page[CourseSummary], response_model_by_alias=True)
async def catalog(response: Response, _: Employee = Depends(current_user)):
    _stub(response)
    return Page(items=SUMMARIES)


@router.get("/my", response_model=Page[AssignedCourse], response_model_by_alias=True)
async def my_courses(response: Response, _: Employee = Depends(current_user)):
    _stub(response)
    at = datetime(2026, 10, 1, 9, 0)
    return Page(items=[
        AssignedCourse(**SUMMARIES[0].model_dump(), assigned_at=at, due_date=date(2026, 10, 31), progress=P1),
        AssignedCourse(**SUMMARIES[1].model_dump(), assigned_at=at, due_date=date(2026, 10, 31), progress=P2),
    ])


@router.get("/courses/{course_id}", response_model=CourseDetail, response_model_by_alias=True)
async def course(course_id: str, response: Response, _: Employee = Depends(current_user)):
    _stub(response)
    return CourseDetail(
        **SUMMARIES[1].model_dump(),
        passing_score=80,
        assigned=True,
        lessons=[
            LessonOut(id="l-saf-1", ord=1, title="Зона конвейера", content_md="## Зона конвейера\nНе заходите за жёлтую линию…", completed=True),
            LessonOut(id="l-saf-2", ord=2, title="Подъём грузов", content_md="## Подъём грузов\nГруз тяжелее 20 кг — вдвоём…", completed=False),
            LessonOut(id="l-saf-3", ord=3, title="Аварийная остановка", content_md="## Аварийная остановка\nКрасная кнопка…", completed=False),
        ],
        questions=[
            QuestionOut(id="q-saf-1", ord=1, text="Груз какого веса поднимают вдвоём?", options=["От 10 кг", "От 20 кг", "От 50 кг"]),
            QuestionOut(id="q-saf-2", ord=2, text="Что делать при заклинивании ленты?", options=["Достать рукой", "Нажать аварийную остановку", "Позвать коллегу"]),
        ],
        progress=P2,
    )


@router.get("/courses/{course_id}/progress", response_model=CourseProgress, response_model_by_alias=True)
async def progress(course_id: str, response: Response, _: Employee = Depends(current_user)):
    _stub(response)
    return P2


@router.post("/lessons/{lesson_id}/complete", response_model=CourseProgress, response_model_by_alias=True)
async def complete_lesson(lesson_id: str, response: Response, _: Employee = Depends(current_user)):
    _stub(response)
    return P2.model_copy(update={"completed_lesson_ids": ["l-saf-1", lesson_id], "lessons_percent": 67})


@router.post("/courses/{course_id}/submit", response_model=SubmitOut, response_model_by_alias=True)
async def submit(course_id: str, body: SubmitIn, response: Response, _: Employee = Depends(current_user)):
    _stub(response)
    done = P2.model_copy(update={"status": "Completed", "score_percent": 100, "passed": True, "lessons_percent": 100})
    return SubmitOut(score=100, passed=True, passing_score=80, correct=2, total=2, progress=done)


@router.post("/assignments", response_model=AssignmentOut, response_model_by_alias=True, status_code=201)
async def assign(body: AssignIn, response: Response, user: Employee = Depends(current_user)):
    _stub(response)
    return AssignmentOut(id="asg-stub", employee_id=body.employee_id, course_id=body.course_id, assigned_by=user.id, assigned_at=datetime(2026, 10, 17, 9, 0), due_date=body.due_date)


@router.get("/progress", response_model=Page[ProgressRow], response_model_by_alias=True)
async def team_progress(response: Response, unit_id: str | None = None, _: Employee = Depends(current_user)):
    _stub(response)
    return Page(items=[ProgressRow(employee_id="emp-aigerim", employee_name="Айгерим Сейткали", unit_id="kz-almaty-sc-b", course_id=C2, course_title=SUMMARIES[1].title, due_date=date(2026, 10, 31), progress=P2)])
