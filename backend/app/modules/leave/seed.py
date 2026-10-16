"""Заявки на отпуск в разных статусах (CLAUDE.md §11)."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.core.requests.models import Request
from app.modules.leave.service import TYPE, days_inclusive
from app.seed.loader import at_time, emp_id


async def _submit(session: AsyncSession, login: str, start_in_days: int, length: int, comment: str, key: str) -> Request:
    emp = await session.get(Employee, emp_id(login))
    assert emp is not None
    start = clock.today() + timedelta(days=start_in_days)
    end = start + timedelta(days=length - 1)
    payload = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "requestedDays": days_inclusive(start, end),
        "comment": comment,
    }
    return await requests.create(session, emp, TYPE, payload, key)


async def _manager(session: AsyncSession, login: str) -> Employee:
    emp = await session.get(Employee, emp_id(login))
    assert emp is not None
    return emp


async def seed(session: AsyncSession) -> None:
    now = clock.now()
    erlan, gulnara = await _manager(session, "erlan"), await _manager(session, "gulnara")

    # Нурлан: два отказа за полгода, с причинами (сигнал rejections для радара).
    # Второй отказ Ерлан дал на 3-й день — позже срока 48 ч (сигнал slow_answers, рентген)
    rejections = ((120, 1, "PEAK_LOAD", "Пиковая нагрузка: распродажа 11.11"), (45, 3, "TEAM_OVERLAP", "В эти даты в смене уже двое в отпуске"))
    for days_ago, decided_after, code, reason in rejections:
        with at_time(now - timedelta(days=days_ago)):
            req = await _submit(session, "nurlan", 20, 5, "Семейные обстоятельства", f"seed-nurlan-{days_ago}")
        with at_time(now - timedelta(days=days_ago - decided_after)):
            await requests.decide(session, erlan, req.id, "Rejected", reason_code=code, comment=reason)

    # Нурлан: отпуск, который Ерлан одобрил через 4 дня (позже срока)
    with at_time(now - timedelta(days=70)):
        req = await _submit(session, "nurlan", 15, 2, "Свадьба друга", "seed-nurlan-70")
    with at_time(now - timedelta(days=66)):
        await requests.decide(session, erlan, req.id, "Approved")

    # Асель: одобренный отпуск
    with at_time(now - timedelta(days=60)):
        req = await _submit(session, "asel", 10, 7, "", "seed-asel-60")
    with at_time(now - timedelta(days=59)):
        await requests.decide(session, gulnara, req.id, "Approved")

    # Айгерим: отпуск, одобренный в прошлом месяце (с приказом в Documentolog)
    with at_time(now - timedelta(days=40)):
        req = await _submit(session, "aigerim", 10, 3, "Свадьба сестры", "seed-aigerim-past")
    with at_time(now - timedelta(days=37)):  # тоже позже срока: у Ерлана 3 решения с опозданием
        await requests.decide(session, erlan, req.id, "Approved")

    # Айгерим: отпуск на рассмотрении у Ерлана (2 часа назад, срок по политике — 48 ч)
    with at_time(now - timedelta(hours=2)):
        await _submit(session, "aigerim", 14, 7, "Поездка к родителям", "seed-aigerim-1")

    # Бакыт (KG): отпуск на рассмотрении у Айбека
    with at_time(now - timedelta(hours=5)):
        await _submit(session, "bakyt", 21, 5, "Той у брата", "seed-bakyt-1")
