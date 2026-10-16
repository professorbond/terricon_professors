from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.modules.ext_guarantees.models import Policy, Reason
from app.seed.loader import load_json


async def seed(session: AsyncSession) -> None:
    for row in load_json("ext/policies.json"):
        session.add(Policy(**row, updated_at=clock.now()))
    for row in load_json("ext/reasons.json"):
        session.add(Reason(code=row["code"], title_key=f"reason.{row['code']}", applies_to=row["applies_to"]))
    await session.flush()
