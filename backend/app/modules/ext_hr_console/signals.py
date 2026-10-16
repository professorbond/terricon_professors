"""Сигналы риска — ТОЛЬКО ошибки компании (CLAUDE.md §7.5). Модуль не читает выводы «Зарплаты по факту»,
вопросы к AI, время прихода и другие поведенческие данные (это проверяет тест)."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.core.org.models import Employee
from app.core.requests.models import OPEN_STATUSES, REJECTED, Request
from app.integrations.zup import get_zup
from app.modules.ext_guarantees.policies import country_setting, guarantee_for
from app.modules.ext_hr_console.models import RiskSignal, SalaryReview

KINDS = ("no_review", "rejections", "pay_equity", "slow_answers", "open_grievance")
HR_ADDRESSED = ("hr_question", "grievance")


def months_between(earlier: datetime | Any, later: datetime | Any) -> int:
    return (later.year - earlier.year) * 12 + later.month - earlier.month - (later.day < earlier.day)


async def detect(session: AsyncSession, emp: Employee, now: datetime) -> dict[str, dict[str, Any]]:
    """Сигналы сотрудника: {kind: details}."""
    found: dict[str, dict[str, Any]] = {}
    zup = get_zup()
    today = now.astimezone(clock.DEFAULT_TZ).date()  # календарь компании, не UTC
    attrs = await zup.get_hr_attrs(session, emp.id)
    salary = await zup.get_salary(session, emp.id)

    # 1. Давно не было пересмотра зарплаты (и пересмотр ещё не предложен)
    period = await country_setting(session, emp.country, "review_period_months")
    if attrs and attrs.last_salary_review_date:
        proposed = (
            await session.scalars(
                select(SalaryReview).where(SalaryReview.employee_id == emp.id, SalaryReview.proposed_at.isnot(None))
            )
        ).first()
        months = months_between(attrs.last_salary_review_date, today)
        if months >= period and proposed is None:
            found["no_review"] = {"months": months, "lastReview": attrs.last_salary_review_date.isoformat()}

    reqs = list(await session.scalars(select(Request).where(Request.employee_id == emp.id)))

    # 2. ≥2 отказов за 180 дней (решения людей, не системы)
    rejected = [r for r in reqs if r.status == REJECTED and r.decided_at and r.decided_at >= now - timedelta(days=180) and not r.decided_by_system]
    if len(rejected) >= 2:
        found["rejections"] = {"count": len(rejected), "numbers": [r.number for r in rejected]}

    # 3. Новичку на тот же грейд в той же стране предложили больше, чем получает сотрудник
    if attrs and salary:
        offers = [
            o for o in await zup.list_recent_offers(session, now - timedelta(days=90))
            if o.grade_code == attrs.grade_code and o.country == emp.country and o.offered_monthly_base > salary.monthly_base
        ]
        if offers:
            best = max(offers, key=lambda o: o.offered_monthly_base)
            found["pay_equity"] = {"grade": attrs.grade_code, "offer": best.offered_monthly_base, "salary": salary.monthly_base}

    # 4. ≥2 заявок за 90 дней решены позже срока или системой по истечении срока
    late = []
    for r in reqs:
        if r.decided_at is None or r.created_at < now - timedelta(days=90):
            continue
        g = await guarantee_for(session, r.id)
        if g and (r.decided_at > g.deadline_at or g.resolution in ("auto_approved", "escalated")):
            late.append(r.number)
    if len(late) >= 2:
        found["slow_answers"] = {"count": len(late), "numbers": late}

    # 5. Вопрос к HR / обращение без решения дольше срока
    for r in reqs:
        if r.type in HR_ADDRESSED and r.status in OPEN_STATUSES:
            g = await guarantee_for(session, r.id)
            if g and now > g.deadline_at:
                found["open_grievance"] = {"number": r.number, "days": (now - r.created_at).days}
                break
    return found


async def recalculate(session: AsyncSession, now: datetime) -> None:
    """Пересчёт: новые сигналы открываются, исчезнувшие причины — закрываются. Действия HR сохраняются."""
    people = await session.scalars(select(Employee).where(Employee.active, Employee.role != "HRAdmin"))
    for emp in list(people):
        found = await detect(session, emp, now)
        current = {
            s.kind: s
            for s in await session.scalars(
                select(RiskSignal).where(RiskSignal.employee_id == emp.id, RiskSignal.status != "resolved")
            )
        }
        for kind, details in found.items():
            if kind in current:
                current[kind].details = details
            else:
                session.add(RiskSignal(id=new_id(), employee_id=emp.id, kind=kind, details=details, detected_at=now))
        for kind, signal in current.items():
            if kind not in found and signal.status == "open":
                signal.status = "resolved"
    await session.flush()
