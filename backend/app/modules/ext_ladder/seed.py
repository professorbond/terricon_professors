from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ext_ladder.models import GradeLadder
from app.seed.loader import load_json


async def seed(session: AsyncSession) -> None:
    for row in load_json("ext/grades.json"):
        session.add(GradeLadder(**row, title_key=f"grade.{row['code']}"))
    await session.flush()
