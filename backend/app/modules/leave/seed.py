from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.seed.loader import at_time, emp_id
from app.modules.leave.service import TYPE, days_inclusive


async def _submit(session: AsyncSession, login: str, start_in_days: int, length: int, comment: str, key: str):
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


async def seed(session: AsyncSession) -> None:
    now = clock.now()
    erlan = await session.get(Employee, emp_id("erlan"))
    gulnara = await session.get(Employee, emp_id("gulnara"))
    assert erlan and gulnara

    # Нурлан: два отказа за полгода (сигнал rejections для радара)
    for days_ago, comment in ((120, "Пиковая нагрузка: распродажа 11.11"), (45, "В эти даты в смене уже двое в отпуске")):
        with at_time(now - timedelta(days=days_ago)):
            req = await _submit(session, "nurlan", 20, 5, "Семейные обстоятельства", f"seed-nurlan-{days_ago}")
        with at_time(now - timedelta(days=days_ago - 1)):
            await requests.decide(session, erlan, req.id, "Rejected", comment=comment)

    # Асель: одобренный отпуск в прошлом (приказ ушёл в 1С — остаток уменьшен)
    with at_time(now - timedelta(days=60)):
        req = await _submit(session, "asel", 10, 7, "", "seed-asel-60")
    with at_time(now - timedelta(days=59)):
        await requests.decide(session, gulnara, req.id, "Approved")

    # Айгерим: отпуск на рассмотрении у Ерлана (2 часа назад)
    with at_time(now - timedelta(hours=2)):
        await _submit(session, "aigerim", 14, 7, "Поездка к родителям", "seed-aigerim-1")
