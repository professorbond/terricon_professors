"""Вопросы без ответа для демо: «23 вопроса про оплату ночных смен (KZ)» и ещё две темы. Без имён."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.modules.ai_jana import public as ai

NIGHT = [
    "Как оплачиваются ночные смены?", "Сколько доплачивают за ночную смену?", "Какая доплата за ночные смены?",
    "Оплачиваются ли ночные смены больше дневных?", "Ночные смены оплачиваются по двойному тарифу?",
    "Где написано про оплату ночных смен?", "Какой коэффициент за ночные смены?", "Почему за ночные смены платят столько же?",
]
SICK = ["Как оформить больничный?", "Куда отправить больничный лист?", "Оплачивается ли больничный с первого дня?"]
WEAR = ["Где получить спецодежду?", "Положена ли спецодежда сортировщику?"]


async def seed(session: AsyncSession) -> None:
    from app.modules.ext_kb_gaps.grouping import assign

    now = clock.now()
    batch = [(NIGHT[i % len(NIGHT)], i) for i in range(23)] + [(SICK[i % len(SICK)], 30 + i) for i in range(6)] + [(WEAR[i % 2], 40 + i) for i in range(4)]
    for text, i in batch:
        q = ai.KbQuestion(id=new_id(), country="KZ", question=text, answered=False, top_score=0.2, asked_at=now - timedelta(hours=3 * i + 1))
        session.add(q)
        await session.flush()
        await assign(session, q)
