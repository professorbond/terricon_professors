from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.org.models import Employee
from app.modules.ext_ladder import service
from app.modules.ext_ladder.models import GradeLadder
from app.modules.ext_ladder.schemas import CourseTag, GradeOut, LadderOut

router = APIRouter(prefix="/api/ext/ladder", tags=["ext: ladder"])


@router.get("/me", response_model=LadderOut, response_model_by_alias=True)
async def my_ladder(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Свой грейд и только следующий: вилки других грейдов и зарплаты других людей не возвращаются."""
    return await service.ladder(session, user, user.lang)


@router.get("/course-tags", response_model=list[CourseTag], response_model_by_alias=True)
async def course_tags(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Бейдж в Academy «Нужен для грейда SORT-2». Без вилок — только код и название грейда."""
    tags = await service.grades_for_course(session, user.country)
    return [
        CourseTag(course_id=cid, grades=[g.model_copy(update={"band_min": 0, "band_max": 0}) for g in (service.grade_out(x, user.lang) for x in grades)])
        for cid, grades in tags.items()
    ]


@router.get("/grades", response_model=list[GradeOut], response_model_by_alias=True)
async def grades(country: str | None = None, user: Employee = Depends(rbac.require_role(rbac.HR)), session: AsyncSession = DbSession):
    q = select(GradeLadder).order_by(GradeLadder.country, GradeLadder.band_min)
    if country:
        q = q.where(GradeLadder.country == country)
    return [service.grade_out(g, user.lang) for g in await session.scalars(q)]
