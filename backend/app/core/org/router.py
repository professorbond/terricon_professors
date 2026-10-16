"""Профиль и оргструктура: кадровые данные только для чтения (источник — 1С:ЗУП)."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.org.models import Employee, Unit
from app.core.org.service import get_employee, get_unit, list_team
from app.core.schemas import ApiModel, Page
from app.integrations.zup import get_zup

router = APIRouter(prefix="/api", tags=["profile"])

COMPANY = "Jana Post"


class PersonRef(ApiModel):
    id: str
    display_name: str


class LeaveBalance(ApiModel):
    days: int
    as_of: date


class EmployeeProfile(ApiModel):
    """Совпадает с EmployeeProfile фронтенда (+ role, country, unit, grade)."""

    id: str
    display_name: str
    company: str
    position: str
    department: str
    unit_kind: str | None
    manager: PersonRef | None
    hired_on: date
    leave_balance: LeaveBalance | None
    role: str
    country: str
    lang: str
    qualification: str | None
    grade_code: str | None
    # Зарплатные поля — только самому сотруднику и HR (rbac.can_view_salary)
    monthly_base: int | None = None


async def build_profile(session: AsyncSession, viewer: Employee, emp: Employee) -> EmployeeProfile:
    unit: Unit | None = await get_unit(session, emp.unit_id)
    manager = await session.get(Employee, emp.manager_id) if emp.manager_id else None
    zup = get_zup()
    attrs = await zup.get_hr_attrs(session, emp.id)
    salary = await zup.get_salary(session, emp.id) if rbac.can_view_salary(viewer, emp) else None
    return EmployeeProfile(
        id=emp.id,
        display_name=emp.full_name,
        company=COMPANY,
        position=emp.position,
        department=unit.name if unit else "—",
        unit_kind=unit.kind if unit else None,
        manager=PersonRef(id=manager.id, display_name=manager.full_name) if manager else None,
        hired_on=emp.hire_date,
        leave_balance=LeaveBalance(days=attrs.vacation_days_left, as_of=attrs.vacation_as_of) if attrs else None,
        role=emp.role,
        country=emp.country,
        lang=emp.lang,
        qualification=emp.qualification,
        grade_code=attrs.grade_code if attrs else None,
        monthly_base=salary.monthly_base if salary else None,
    )


@router.get("/profile/me", response_model=EmployeeProfile, response_model_by_alias=True)
async def my_profile(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await build_profile(session, user, user)


@router.get("/employees/{employee_id}", response_model=EmployeeProfile, response_model_by_alias=True)
async def employee_profile(
    employee_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession
):
    emp = await get_employee(session, employee_id)
    rbac.ensure(rbac.can_view_employee(user, emp), "Нет доступа к профилю этого сотрудника")
    return await build_profile(session, user, emp)


@router.get("/team", response_model=Page[EmployeeProfile], response_model_by_alias=True)
async def my_team(
    user: Employee = Depends(rbac.require_role(rbac.MANAGER)), session: AsyncSession = DbSession
):
    return Page(items=[await build_profile(session, user, e) for e in await list_team(session, user.id)])


@router.get("/employees", response_model=Page[EmployeeProfile], response_model_by_alias=True)
async def all_employees(
    country: str | None = None,
    user: Employee = Depends(rbac.require_role(rbac.HR)),
    session: AsyncSession = DbSession,
):
    q = select(Employee).where(Employee.active).order_by(Employee.full_name)
    if country:
        q = q.where(Employee.country == country)
    return Page(items=[await build_profile(session, user, e) for e in await session.scalars(q)])
