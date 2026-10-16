from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.org.models import Employee
from app.core.org.service import list_team
from app.core.schemas import Page
from app.modules.academy import service
from app.modules.academy.models import Assignment, Course
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

router = APIRouter(prefix="/api/academy", tags=["academy"])


def summary(course: Course, lang: str) -> CourseSummary:
    return CourseSummary(
        id=course.id,
        title=service.title(course, lang),
        description=service.description(course, lang),
        duration_minutes=course.duration_min,
    )


@router.get("/courses", response_model=Page[CourseSummary], response_model_by_alias=True)
async def catalog(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return Page(items=[summary(c, user.lang) for c in await service.catalog(session, user)])


@router.get("/my", response_model=Page[AssignedCourse], response_model_by_alias=True)
async def my_courses(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    items = []
    for a in await service.list_assignments(session, user.id):
        course = await session.get(Course, a.course_id)
        assert course is not None
        items.append(
            AssignedCourse(
                **summary(course, user.lang).model_dump(),
                assigned_at=a.assigned_at,
                due_date=a.due_date,
                progress=await service.progress(session, user.id, course.id),
            )
        )
    return Page(items=items)


@router.get("/courses/{course_id}", response_model=CourseDetail, response_model_by_alias=True)
async def course_detail(course_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    course = await service.visible_course(session, user, course_id)
    prog = await service.progress(session, user.id, course_id)
    done = set(prog.completed_lesson_ids)
    return CourseDetail(
        **summary(course, user.lang).model_dump(),
        passing_score=course.passing_score,
        assigned=await service.get_assignment(session, user.id, course_id) is not None,
        lessons=[
            LessonOut(id=l.id, ord=l.ord, title=l.title, content_md=l.content_md, completed=l.id in done)
            for l in await service.lessons(session, course_id)
        ],
        # Правильные ответы не отдаются никогда
        questions=[
            QuestionOut(id=q.id, ord=q.ord, text=q.text, options=q.options)
            for q in await service.questions(session, course_id)
        ],
        progress=prog,
    )


@router.get("/courses/{course_id}/progress", response_model=CourseProgress, response_model_by_alias=True)
async def course_progress(course_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    await service.visible_course(session, user, course_id)
    return await service.progress(session, user.id, course_id)


@router.post("/lessons/{lesson_id}/complete", response_model=CourseProgress, response_model_by_alias=True)
async def complete_lesson(lesson_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await service.complete_lesson(session, user, lesson_id)


@router.post("/courses/{course_id}/submit", response_model=SubmitOut, response_model_by_alias=True)
async def submit(
    course_id: str, body: SubmitIn, user: Employee = Depends(current_user), session: AsyncSession = DbSession
):
    attempt, correct, total = await service.submit(session, user, course_id, body.answers)
    course = await session.get(Course, course_id)
    assert course is not None
    return SubmitOut(
        score=attempt.score,
        passed=attempt.passed,
        passing_score=course.passing_score,
        correct=correct,
        total=total,
        progress=await service.progress(session, user.id, course_id),
    )


@router.post("/assignments", response_model=AssignmentOut, response_model_by_alias=True, status_code=201)
async def assign(
    body: AssignIn,
    user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)),
    session: AsyncSession = DbSession,
):
    a = await service.assign(session, user, body.employee_id, body.course_id, body.due_date)
    return AssignmentOut(
        id=a.id,
        employee_id=a.employee_id,
        course_id=a.course_id,
        assigned_by=a.assigned_by,
        assigned_at=a.assigned_at,
        due_date=a.due_date,
    )


@router.get("/progress", response_model=Page[ProgressRow], response_model_by_alias=True)
async def team_progress(
    unit_id: str | None = Query(default=None, alias="unitId"),
    country: str | None = None,
    user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)),
    session: AsyncSession = DbSession,
):
    """Прогресс обучения: руководитель — своя команда, HR — все (фильтры по подразделению и стране)."""
    if user.role == rbac.MANAGER:
        people = await list_team(session, user.id)
    else:
        q = select(Employee).where(Employee.active)
        if unit_id:
            q = q.where(Employee.unit_id == unit_id)
        if country:
            q = q.where(Employee.country == country)
        people = list(await session.scalars(q))
    by_id = {p.id: p for p in people}
    rows = await session.scalars(
        select(Assignment).where(Assignment.employee_id.in_(by_id)).order_by(Assignment.assigned_at)
    )
    items = []
    for a in rows:
        course = await session.get(Course, a.course_id)
        assert course is not None
        emp = by_id[a.employee_id]
        items.append(
            ProgressRow(
                employee_id=emp.id,
                employee_name=emp.full_name,
                unit_id=emp.unit_id,
                course_id=course.id,
                course_title=service.title(course, user.lang),
                due_date=a.due_date,
                progress=await service.progress(session, emp.id, course.id),
            )
        )
    return Page(items=items)
