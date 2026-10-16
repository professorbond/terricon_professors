from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, rbac
from app.core.errors import conflict, forbidden, not_found, validation
from app.core.events import events
from app.core.ids import new_id
from app.core.notifications import notify
from app.core.org.models import Employee
from app.core.org.service import get_employee
from app.modules.academy.models import Assignment, Attempt, Course, Lesson, LessonProgress, Question
from app.modules.academy.schemas import CourseProgress


def title(course: Course, lang: str) -> str:
    return course.title_kk if lang == "kk" and course.title_kk else course.title


def description(course: Course, lang: str) -> str:
    return course.description_kk if lang == "kk" and course.description_kk else course.description


async def visible_course(session: AsyncSession, user: Employee, course_id: str) -> Course:
    course = await session.get(Course, course_id)
    if course is None or not course.active or (course.country and course.country != user.country):
        raise not_found("Курс не найден")
    return course


async def catalog(session: AsyncSession, user: Employee) -> list[Course]:
    q = select(Course).where(Course.active, (Course.country.is_(None)) | (Course.country == user.country))
    return list(await session.scalars(q.order_by(Course.title)))


async def lessons(session: AsyncSession, course_id: str) -> list[Lesson]:
    return list(await session.scalars(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.ord)))


async def questions(session: AsyncSession, course_id: str) -> list[Question]:
    return list(await session.scalars(select(Question).where(Question.course_id == course_id).order_by(Question.ord)))


async def get_assignment(session: AsyncSession, employee_id: str, course_id: str) -> Assignment | None:
    q = select(Assignment).where(Assignment.employee_id == employee_id, Assignment.course_id == course_id)
    return (await session.scalars(q)).first()


async def list_assignments(session: AsyncSession, employee_id: str) -> list[Assignment]:
    q = select(Assignment).where(Assignment.employee_id == employee_id).order_by(Assignment.assigned_at)
    return list(await session.scalars(q))


async def progress(session: AsyncSession, employee_id: str, course_id: str) -> CourseProgress:
    lesson_ids = [lesson.id for lesson in await lessons(session, course_id)]
    done_rows = await session.scalars(
        select(LessonProgress.lesson_id).where(
            LessonProgress.employee_id == employee_id, LessonProgress.lesson_id.in_(lesson_ids)
        )
    )
    done = set(done_rows)
    completed = [lid for lid in lesson_ids if lid in done]
    attempts = list(
        await session.scalars(select(Attempt).where(Attempt.employee_id == employee_id, Attempt.course_id == course_id))
    )
    passed = any(a.passed for a in attempts)
    best = max((a.score for a in attempts), default=None)
    if passed:
        status = "Completed"
    elif completed or attempts:
        status = "InProgress"
    else:
        status = "Assigned"
    total = len(lesson_ids)
    return CourseProgress(
        course_id=course_id,
        completed_lesson_ids=completed,
        total_lessons=total,
        status=status,
        score_percent=best,
        passed=passed,
        lessons_percent=round(len(completed) * 100 / total) if total else 0,
    )


async def complete_lesson(session: AsyncSession, user: Employee, lesson_id: str) -> CourseProgress:
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("Урок не найден")
    await visible_course(session, user, lesson.course_id)
    if await session.get(LessonProgress, (user.id, lesson_id)) is None:  # идемпотентно
        session.add(LessonProgress(employee_id=user.id, lesson_id=lesson_id, completed_at=clock.now()))
        await session.flush()
    return await progress(session, user.id, lesson.course_id)


async def submit(session: AsyncSession, user: Employee, course_id: str, answers: list[int]) -> tuple[Attempt, int, int]:
    course = await visible_course(session, user, course_id)
    qs = await questions(session, course_id)
    if len(answers) != len(qs):
        raise validation("ANSWERS_MISMATCH", f"Нужно ответить на все вопросы: {len(qs)}", "answers", {"total": len(qs)})
    already_passed = (await progress(session, user.id, course_id)).passed
    correct = sum(1 for q, a in zip(qs, answers, strict=True) if q.correct_index == a)
    score = round(correct * 100 / len(qs)) if qs else 100
    attempt = Attempt(
        id=new_id(),
        employee_id=user.id,
        course_id=course_id,
        score=score,
        passed=score >= course.passing_score,
        submitted_at=clock.now(),
    )
    session.add(attempt)
    await session.flush()
    if attempt.passed and not already_passed:
        await notify(
            session,
            user.id,
            "academy.completed",
            "notif.academy.completed.title",
            "notif.academy.completed.body",
            {"course": course.title, "score": score},
            {"kind": "course", "courseId": course_id},
        )
        # Подписчики: «Открытая лестница» (прогресс по грейду)
        await events.emit("academy.course_completed", session=session, employee=user, course=course, score=score)
    return attempt, correct, len(qs)


async def assign(
    session: AsyncSession, actor: Employee, employee_id: str, course_id: str, due_date: date | None
) -> Assignment:
    employee = await get_employee(session, employee_id)
    if not (actor.role == rbac.HR or rbac.is_my_team(actor, employee)):
        raise forbidden("Назначать курсы можно только своей команде")
    course = await visible_course(session, employee, course_id)
    if due_date is not None and due_date < clock.today():
        raise validation("INVALID_DATES", "Срок не может быть в прошлом", "dueDate")
    if await get_assignment(session, employee_id, course_id) is not None:
        raise conflict("ALREADY_ASSIGNED", "Курс уже назначен этому сотруднику")
    a = Assignment(
        id=new_id(),
        employee_id=employee_id,
        course_id=course_id,
        assigned_by=actor.id,
        assigned_at=clock.now(),
        due_date=due_date,
    )
    session.add(a)
    await session.flush()
    body = "notif.academy.assigned.body_due" if due_date else "notif.academy.assigned.body"
    await notify(
        session,
        employee_id,
        "academy.assigned",
        "notif.academy.assigned.title",
        body,
        {"course": course.title, "due": due_date.strftime("%d.%m.%Y") if due_date else None},
        {"kind": "course", "courseId": course_id},
    )
    await events.emit("academy.assigned", session=session, assignment=a, actor=actor)
    return a


async def has_passed(session: AsyncSession, employee_id: str, course_id: str) -> bool:
    """Публичный сервис для других модулей (лестница)."""
    q = select(Attempt.id).where(Attempt.employee_id == employee_id, Attempt.course_id == course_id, Attempt.passed)
    return (await session.scalars(q)).first() is not None
