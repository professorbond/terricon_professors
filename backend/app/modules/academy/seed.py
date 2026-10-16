from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.org.models import Employee
from app.modules.academy import service
from app.modules.academy.models import Course, Lesson, Question
from app.seed.loader import at_time, emp_id, load_json

RETURNS, SAFETY = "course-returns", "course-safety"


async def seed(session: AsyncSession) -> None:
    for row in load_json("academy/courses.json"):
        session.add(
            Course(
                id=row["id"],
                title=row["title"],
                title_kk=row.get("title_kk"),
                description=row["description"],
                description_kk=row.get("description_kk"),
                duration_min=row["duration_min"],
                passing_score=row["passing_score"],
            )
        )
        for i, lesson in enumerate(row["lessons"], 1):
            session.add(Lesson(id=lesson["id"], course_id=row["id"], ord=i, title=lesson["title"], content_md=lesson["content_md"]))
        for i, q in enumerate(row["questions"], 1):
            session.add(
                Question(id=f"{row['id']}-q{i}", course_id=row["id"], ord=i, text=q["text"], options=q["options"], correct_index=q["correct"])
            )
    await session.flush()

    async def emp(login: str) -> Employee:
        e = await session.get(Employee, emp_id(login))
        assert e is not None
        return e

    erlan, gulnara, aibek = await emp("erlan"), await emp("gulnara"), await emp("aibek")
    aigerim, nurlan, asel, bakyt = await emp("aigerim"), await emp("nurlan"), await emp("asel"), await emp("bakyt")
    now = clock.now()

    # Айгерим: «Работа с возвратами» пройден месяц назад (1 из 2 курсов для SORT-2)
    with at_time(now - timedelta(days=30)):
        await service.assign(session, erlan, aigerim.id, RETURNS, None)
    with at_time(now - timedelta(days=25)):
        for lid in ("l-ret-1", "l-ret-2", "l-ret-3"):
            await service.complete_lesson(session, aigerim, lid)
        await service.submit(session, aigerim, RETURNS, [1, 1, 1])
    # «Техника безопасности» назначена вчера, пройден 1 урок; уведомление «Назначен курс» не прочитано
    with at_time(now - timedelta(hours=20)):
        await service.assign(session, erlan, aigerim.id, SAFETY, clock.today() + timedelta(days=14))
        await service.complete_lesson(session, aigerim, "l-saf-1")

    # Остальным — для отчёта о прогрессе
    with at_time(now - timedelta(days=10)):
        await service.assign(session, erlan, nurlan.id, SAFETY, clock.today() + timedelta(days=7))
        await service.assign(session, gulnara, asel.id, RETURNS, None)
        await service.assign(session, aibek, bakyt.id, SAFETY, None)
