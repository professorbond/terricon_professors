"""Seed тестовых данных. Все люди и цифры вымышленные. Пароль у всех: demo1234.

Порядок: справочники и сотрудники → mock 1С:ЗУП → seed модулей (module.seed) в порядке MODULES.
"""

import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.auth import hash_password
from app.core.demo.models import DemoState
from app.core.notifications.models import Notification
from app.core.org.models import Country, Employee, Unit
from app.integrations.zup.models import ZupHireOffer, ZupHrAttrs, ZupSalary, ZupTimesheet

SEED_DIR = Path(__file__).parent
DEMO_PASSWORD = "demo1234"
# Увеличивать, когда меняется seed: демо-база пересоздастся при следующем старте
SEED_VERSION = 7


def load_json(relative: str) -> Any:
    data = json.loads((SEED_DIR / relative).read_text(encoding="utf-8"))
    return data["rows"] if isinstance(data, dict) and "rows" in data else data


def emp_id(login: str) -> str:
    return f"emp-{login}"


def months_ago(n: int | None) -> date | None:
    if n is None:
        return None
    today = clock.today()
    month = today.month - n
    year = today.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(today.day, 28))


@contextmanager
def at_time(moment: datetime):
    """Временно «перевести часы» — чтобы seed-заявки получили прошлые даты через обычный движок."""
    saved = clock.offset()
    clock.set_offset(saved + (moment - clock.now()))
    try:
        yield
    finally:
        clock.set_offset(saved)


async def is_seeded(session: AsyncSession) -> bool:
    return bool(await session.scalar(select(func.count()).select_from(Employee)))


async def stored_seed_version(session: AsyncSession) -> int:
    state = await session.get(DemoState, 1)
    return state.seed_version if state else 0


async def seed_core(session: AsyncSession) -> None:
    password_hash = hash_password(DEMO_PASSWORD)
    session.add_all(Country(**row) for row in load_json("core/countries.json"))
    await session.flush()
    for row in load_json("core/units.json"):  # родители идут раньше детей
        session.add(Unit(**row))
        await session.flush()
    rows = load_json("core/employees.json")
    for row in sorted(rows, key=lambda r: r["manager"] is not None):
        session.add(
            Employee(
                id=emp_id(row["login"]),
                login=row["login"],
                password_hash=password_hash,
                full_name=row["full_name"],
                role=row["role"],
                country=row["country"],
                unit_id=row["unit_id"],
                position=row["position"],
                manager_id=emp_id(row["manager"]) if row["manager"] else None,
                hire_date=date.fromisoformat(row["hire_date"]),
                qualification=row["qualification"],
            )
        )
        await session.flush()


async def seed_zup(session: AsyncSession) -> None:
    today = clock.today()
    for row in load_json("zup/salaries.json"):
        session.add(
            ZupSalary(
                employee_id=emp_id(row["login"]),
                monthly_base=row["monthly_base"],
                shift_rate=row["shift_rate"],
                night_bonus_rate=row["night_bonus_rate"],
            )
        )
    for row in load_json("zup/hr_attrs.json"):
        session.add(
            ZupHrAttrs(
                employee_id=emp_id(row["login"]),
                grade_code=row["grade_code"],
                last_salary_review_date=months_ago(row["review_months_ago"]),
                vacation_days_left=row["vacation_days_left"],
                vacation_as_of=date(today.year, 1, 1),
                incidents_last_date=months_ago(row["incident_months_ago"]),
                planned_shifts_per_month=row.get("planned_shifts", 22),
                grade_since=months_ago(row.get("grade_months_ago")),
            )
        )
    month_start = today.replace(day=1)
    for row in load_json("zup/timesheets.json"):
        # Смены с 1-го числа до вчера; если дней в месяце пока мало — сколько поместится
        days = [month_start + timedelta(days=i) for i in range((today - month_start).days)]
        for i, day in enumerate(days[: row["shifts"]]):
            session.add(
                ZupTimesheet(
                    employee_id=emp_id(row["login"]),
                    date=day,
                    hours=row["hours"],
                    shift_type="night" if i < row["night"] else "day",
                )
            )
    for row in load_json("zup/hire_offers.json"):
        session.add(
            ZupHireOffer(
                id=row["id"],
                position=row["position"],
                grade_code=row["grade_code"],
                country=row["country"],
                offered_monthly_base=row["offered_monthly_base"],
                offered_at=clock.now() - timedelta(days=row["days_ago"]),
            )
        )
    await session.flush()


async def run_seed(session: AsyncSession, modules: list) -> None:
    await seed_core(session)
    await seed_zup(session)
    for module in modules:
        if module.seed is not None:
            await module.seed(session)
    state = await session.get(DemoState, 1)
    if state is None:
        state = DemoState(id=1, offset_seconds=0)
        session.add(state)
    state.seed_version = SEED_VERSION
    # История seed старше суток считается прочитанной — в колокольчике только свежее
    await session.execute(
        update(Notification)
        .where(Notification.created_at < clock.now() - timedelta(days=1))
        .values(read_at=Notification.created_at)
    )
    await session.flush()
