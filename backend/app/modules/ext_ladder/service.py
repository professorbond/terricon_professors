from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.i18n import t
from app.core.org.models import Employee
from app.integrations.zup import get_zup
from app.modules.academy import service as academy
from app.modules.academy.models import Course
from app.modules.ext_guarantees.policies import country_setting
from app.modules.ext_hr_console.reviews import proposed_review_date
from app.modules.ext_ladder.models import GradeLadder
from app.modules.ext_ladder.schemas import Criterion, GradeOut, LadderOut

CURRENCY = {"KZ": "KZT", "KG": "KGS"}


def months_since(d: date | None, today: date) -> int | None:
    if d is None:
        return None
    return (today.year - d.year) * 12 + today.month - d.month - (today.day < d.day)


def grade_out(g: GradeLadder, lang: str) -> GradeOut:
    return GradeOut(code=g.code, title=t(g.title_key, lang), band_min=g.band_min, band_max=g.band_max, currency=CURRENCY.get(g.country, "KZT"))


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    return date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


async def next_review(session: AsyncSession, emp: Employee) -> date | None:
    proposed = await proposed_review_date(session, emp.id)
    if proposed:
        return proposed
    attrs = await get_zup().get_hr_attrs(session, emp.id)
    if attrs is None or attrs.last_salary_review_date is None:
        return None
    return add_months(attrs.last_salary_review_date, await country_setting(session, emp.country, "review_period_months"))


async def ladder(session: AsyncSession, emp: Employee, lang: str) -> LadderOut:
    zup = get_zup()
    attrs = await zup.get_hr_attrs(session, emp.id)
    current = await session.get(GradeLadder, attrs.grade_code) if attrs else None
    nxt = await session.get(GradeLadder, current.next_grade_code) if current and current.next_grade_code else None
    criteria: list[Criterion] = []
    if current and nxt:
        for course_id in current.required_course_ids:
            course = await session.get(Course, course_id)
            title = academy.title(course, lang) if course else course_id
            criteria.append(Criterion(kind="course", title=title, course_id=course_id, done=await academy.has_passed(session, emp.id, course_id)))
        today = clock.today()
        if current.min_months_in_grade:
            actual = months_since(attrs.grade_since if attrs else None, today) or months_since(emp.hire_date, today) or 0
            criteria.append(
                Criterion(kind="months_in_grade", title=t("ladder.months_in_grade", lang, {"n": current.min_months_in_grade}),
                          required=current.min_months_in_grade, actual=actual, done=actual >= current.min_months_in_grade)
            )
        if current.min_months_no_incidents:
            last = attrs.incidents_last_date if attrs else None
            actual = months_since(last, today) if last else (months_since(emp.hire_date, today) or 0)
            criteria.append(
                Criterion(kind="no_incidents", title=t("ladder.no_incidents", lang, {"n": current.min_months_no_incidents}),
                          required=current.min_months_no_incidents, actual=actual, done=actual >= current.min_months_no_incidents)
            )
    salary = await zup.get_salary(session, emp.id)
    done = sum(c.done for c in criteria)
    return LadderOut(
        current=grade_out(current, lang) if current else None,
        next=grade_out(nxt, lang) if nxt else None,
        criteria=criteria,
        criteria_done=done,
        criteria_total=len(criteria),
        remaining_courses=sum(1 for c in criteria if c.kind == "course" and not c.done),
        raise_to_next_min=max(0, nxt.band_min - salary.monthly_base) if nxt and salary else None,
        next_review_date=await next_review(session, emp),
        ready=bool(criteria) and done == len(criteria),
    )


async def grades_for_course(session: AsyncSession, country: str) -> dict[str, list[GradeLadder]]:
    """course_id → грейды, для перехода на которые нужен курс (по стране)."""
    out: dict[str, list[GradeLadder]] = {}
    for g in await session.scalars(select(GradeLadder).where(GradeLadder.country == country)):
        if not g.next_grade_code:
            continue
        target = await session.get(GradeLadder, g.next_grade_code)
        for cid in g.required_course_ids:
            if target:
                out.setdefault(cid, []).append(target)
    return out
