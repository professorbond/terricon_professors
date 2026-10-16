from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.seed.loader import at_time, emp_id


async def seed(session: AsyncSession) -> None:
    """Вопрос к HR без ответа, висит 4 дня (дольше срока — для радара)."""
    nurlan = await session.get(Employee, emp_id("nurlan"))
    assert nurlan is not None
    with at_time(clock.now() - timedelta(days=4)):
        await requests.create(
            session,
            nurlan,
            "hr_question",
            {
                "question": "Как оплачиваются ночные смены и где это прописано?",
                "aiContext": "AI Jana: надёжной информации в базе знаний нет.",
            },
            "seed-nurlan-hq",
        )
