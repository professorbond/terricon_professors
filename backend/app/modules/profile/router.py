from fastapi import APIRouter, Depends, Query
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import forbidden
from app.core.notifications.service import unread_count
from app.core.org.models import Employee
from app.core.org.service import get_employee, get_unit, list_team
from app.core.profile import profile_registry
from app.core.schemas import Page
from app.integrations.zup import get_zup
from app.modules.profile.schemas import EmployeeProfile, PersonRef

router = APIRouter(prefix="/api", tags=["profile"])

COMPANY = "Jana Post"


async def build_profile(session: AsyncSession, viewer: Employee, emp: Employee) -> EmployeeProfile:
    unit = await get_unit(session, emp.unit_id)
    manager = await session.get(Employee, emp.manager_id) if emp.manager_id else None
    zup = get_zup()
    attrs = await zup.get_hr_attrs(session, emp.id)
    salary = await zup.get_salary(session, emp.id) if rbac.can_view_salary(viewer, emp) else None
    collected = await profile_registry.collect(session, viewer, emp)
    known = set(EmployeeProfile.model_fields)
    extra = {k: v for k, v in collected.items() if k in known}
    extensions = {
        to_camel(k): (v.model_dump(mode="json", by_alias=True) if hasattr(v, "model_dump") else v)
        for k, v in collected.items()
        if k not in known
    }
    return EmployeeProfile(
        id=emp.id,
        display_name=emp.full_name,
        company=COMPANY,
        position=emp.position,
        department=unit.name if unit else "—",
        manager=PersonRef(id=manager.id, display_name=manager.full_name) if manager else None,
        hired_on=emp.hire_date,
        role=emp.role,
        country=emp.country,
        lang=emp.lang,
        unit_id=emp.unit_id,
        unit_kind=unit.kind if unit else None,
        qualification=emp.qualification,
        grade_code=attrs.grade_code if attrs else None,
        monthly_base=salary.monthly_base if salary else None,
        unread_notifications=await unread_count(session, emp.id) if viewer.id == emp.id else None,
        extensions=extensions,
        **extra,
    )


@router.get("/profile/me", response_model=EmployeeProfile, response_model_by_alias=True)
async def my_profile(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await build_profile(session, user, user)


@router.get("/employees/{employee_id}", response_model=EmployeeProfile, response_model_by_alias=True)
async def employee_profile(employee_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    emp = await get_employee(session, employee_id)
    rbac.ensure(rbac.can_view_employee(user, emp), "Нет доступа к профилю этого сотрудника")
    return await build_profile(session, user, emp)


@router.get("/team", response_model=Page[EmployeeProfile], response_model_by_alias=True)
async def team(
    unit_id: str | None = Query(default=None, alias="unitId"),
    country: str | None = None,
    user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)),
    session: AsyncSession = DbSession,
):
    """Руководитель — своя команда (без зарплат). HR — все, с фильтрами по подразделению и стране."""
    if user.role == rbac.MANAGER:
        if unit_id or country:
            raise forbidden("Фильтры доступны только HR")
        rows = await list_team(session, user.id)
    else:
        q = select(Employee).where(Employee.active).order_by(Employee.full_name)
        if unit_id:
            q = q.where(Employee.unit_id == unit_id)
        if country:
            q = q.where(Employee.country == country)
        rows = list(await session.scalars(q))
    return Page(items=[await build_profile(session, user, e) for e in rows])


@router.get("/employees", response_model=Page[EmployeeProfile], response_model_by_alias=True)
async def all_employees(
    unit_id: str | None = Query(default=None, alias="unitId"),
    country: str | None = None,
    user: Employee = Depends(rbac.require_role(rbac.HR)),
    session: AsyncSession = DbSession,
):
    """То же, что /api/team для HR (синоним)."""
    return await team(unit_id, country, user, session)
