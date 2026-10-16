"""Демо-инструменты: перевод времени, сброс, быстрый вход за персонажей. Только DEMO_MODE=true."""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.auth import issue_token
from app.core.auth_router import LoginOut, user_out
from app.core.db import DbSession
from app.core.demo.service import save_offset, wipe_all
from app.core.errors import not_found, validation
from app.core.org.models import Employee
from app.core.org.service import find_by_login
from app.core.schemas import ApiModel
from app.core.ticks import ticks

router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoStateOut(ApiModel):
    now: datetime
    offset_hours: float


class AdvanceIn(ApiModel):
    hours: float = Field(gt=0, le=24 * 60)


class Persona(ApiModel):
    login: str
    display_name: str
    role: str
    country: str
    position: str


class LoginAsIn(ApiModel):
    """login — конкретный персонаж; role — персонаж по умолчанию для роли (signInDemo фронтенда)."""

    login: str | None = None
    role: Literal["Employee", "Manager", "HRAdmin"] | None = None


DEFAULT_PERSONA = {"Employee": "aigerim", "Manager": "erlan", "HRAdmin": "daniyar"}


def _state() -> DemoStateOut:
    return DemoStateOut(now=clock.now(), offset_hours=clock.offset().total_seconds() / 3600)


@router.get("/state", response_model=DemoStateOut, response_model_by_alias=True)
async def state() -> DemoStateOut:
    return _state()


@router.post("/advance-time", response_model=DemoStateOut, response_model_by_alias=True)
async def advance_time(body: AdvanceIn, session: AsyncSession = DbSession) -> DemoStateOut:
    """Сдвинуть часы вперёд и сразу выполнить тик (сроки гарантий, сигналы)."""
    await save_offset(session, clock.offset() + timedelta(hours=body.hours))
    await ticks.run(session)
    return _state()


@router.post("/reset", response_model=DemoStateOut, response_model_by_alias=True)
async def reset(request: Request, session: AsyncSession = DbSession) -> DemoStateOut:
    """Стереть все данные и заново применить seed. Часы возвращаются к реальному времени."""
    from app.seed.loader import run_seed

    await wipe_all(session)
    await run_seed(session, request.app.state.modules)
    return _state()


@router.get("/personas", response_model=list[Persona], response_model_by_alias=True)
async def personas(session: AsyncSession = DbSession) -> list[Persona]:
    rows = await session.scalars(select(Employee).where(Employee.active).order_by(Employee.country, Employee.role))
    return [
        Persona(login=e.login, display_name=e.full_name, role=e.role, country=e.country, position=e.position)
        for e in rows
    ]


@router.post("/login-as", response_model=LoginOut, response_model_by_alias=True)
async def login_as(body: LoginAsIn, session: AsyncSession = DbSession) -> LoginOut:
    """Вход без пароля за тестового персонажа (демо-панель). В проде роутер не подключается."""
    login = body.login or (DEFAULT_PERSONA[body.role] if body.role else None)
    if login is None:
        raise validation("LOGIN_OR_ROLE_REQUIRED", "Укажите login или role", "login")
    emp = await find_by_login(session, login)
    if emp is None:
        raise not_found("Персонаж не найден")
    return LoginOut(access_token=issue_token(emp), user=user_out(emp))
