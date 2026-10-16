"""11 сотрудников уже «сохранены» радаром (счётчик 9,9 млн ₸ → после демо 10,8 млн ₸) + пересчёт сигналов."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.modules.ext_hr_console.models import RiskSignal
from app.modules.ext_hr_console.signals import recalculate
from app.seed.loader import emp_id

# Исторические случаи (закрыты): кого радар подсветил, HR принял меры, человек остался
HISTORY = [
    ("asel", "no_review", 300), ("erlan", "slow_answers", 280), ("gulnara", "pay_equity", 260), ("nurlan", "no_review", 240),
    ("asel", "rejections", 200), ("erlan", "pay_equity", 180), ("gulnara", "no_review", 160), ("asel", "slow_answers", 140),
    ("nurlan", "pay_equity", 120), ("erlan", "no_review", 100), ("gulnara", "rejections", 90),
]


async def seed(session: AsyncSession) -> None:
    now = clock.now()
    for login, kind, days_ago in HISTORY:
        detected = now - timedelta(days=days_ago)
        session.add(
            RiskSignal(
                id=new_id(), employee_id=emp_id(login), kind=kind, details={"historical": True}, detected_at=detected,
                status="resolved", action="propose_review", actioned_at=detected + timedelta(days=3), retained_confirmed=True,
            )
        )
    await session.flush()
    await recalculate(session, now)
