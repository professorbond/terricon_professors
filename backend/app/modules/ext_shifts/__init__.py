"""Биржа смен, мини-версия (CLAUDE.md §7.8). Флаг: shifts.

«Отдать смену» — коллега того же центра и квалификации берёт её; руководитель видит, но не согласует.
«Открытая смена» — руководитель/HR публикует с оплатой, сотрудник берёт в одно нажатие."""

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import AppError, forbidden, validation
from app.core.modules import BackendModule, ModuleContext
from app.core.org.models import Employee, Unit
from app.core.schemas import ApiModel, Page
from app.modules.ext_shifts import service
from app.modules.ext_shifts.models import Shift, ShiftEvent
from app.modules.ext_shifts.seed import seed

RU = {
    "notif.shift.taken.title": "Смена ваша",
    "notif.shift.taken.body": "{when}: +{pay} к заработку",
    "notif.shift.given.title": "Вашу смену взяли",
    "notif.shift.given.body": "{when}: смену взял(а) {name}",
}
KK = {
    "notif.shift.taken.title": "Ауысым сіздікі",
    "notif.shift.taken.body": "{when}: табысқа +{pay}",
    "notif.shift.given.title": "Ауысымыңызды алды",
    "notif.shift.given.body": "{when}: ауысымды {name} алды",
}

router = APIRouter(prefix="/api/ext/shifts", tags=["ext: shifts"])


class ShiftOut(ApiModel):
    id: str
    center_id: str
    center_name: str
    date: date
    start_time: str
    end_time: str
    qualification: str
    status: str
    assignee_id: str | None
    assignee_name: str | None
    pay_preview: int | None  # сколько заработает текущий пользователь, если возьмёт / уже взял
    mine: bool
    version: int


class ShiftEventOut(ApiModel):
    at: datetime
    event: str
    actor_name: str | None


class TeamShiftOut(ShiftOut):
    history: list[ShiftEventOut]


class PublishIn(ApiModel):
    date: date
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    qualification: str = "sorter"
    pay_preview: int = Field(gt=0)
    center_id: str | None = None  # для HR; руководитель публикует в своём центре


async def out(session: AsyncSession, s: Shift, viewer: Employee) -> ShiftOut:
    center = await session.get(Unit, s.center_id)
    assignee = await session.get(Employee, s.assignee_id) if s.assignee_id else None
    return ShiftOut(
        id=s.id, center_id=s.center_id, center_name=center.name if center else "—", date=s.date, start_time=s.start_time,
        end_time=s.end_time, qualification=s.qualification, status=s.status, assignee_id=s.assignee_id,
        assignee_name=assignee.full_name if assignee else None, pay_preview=await service.pay_for(session, viewer, s),
        mine=s.assignee_id == viewer.id, version=s.version,
    )


@router.get("/my", response_model=Page[ShiftOut], response_model_by_alias=True)
async def my(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return Page(items=[await out(session, s, user) for s in await service.my_shifts(session, user)])


@router.get("/available", response_model=Page[ShiftOut], response_model_by_alias=True)
async def available(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Смены, которые пользователь может взять прямо сейчас (все проверки уже пройдены)."""
    center = await service.center_of(session, user.unit_id)
    rows = await session.scalars(
        select(Shift).where(Shift.center_id == center, Shift.status.in_(("offered", "open")), Shift.date >= clock.today()).order_by(Shift.date, Shift.start_time)
    )
    items = []
    for s in rows:
        try:
            await service.check_can_take(session, user, s)
        except AppError:
            continue
        items.append(await out(session, s, user))
    return Page(items=items)


@router.post("/{shift_id}/offer", response_model=ShiftOut, response_model_by_alias=True)
async def offer(shift_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await out(session, await service.offer(session, user, shift_id), user)


@router.post("/{shift_id}/cancel-offer", response_model=ShiftOut, response_model_by_alias=True)
async def cancel_offer(shift_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await out(session, await service.cancel_offer(session, user, shift_id), user)


@router.post("/{shift_id}/take", response_model=ShiftOut, response_model_by_alias=True)
async def take(shift_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Взять смену в одно нажатие. Руководитель не согласует — правила проверяет система."""
    s, _pay = await service.take(session, user, shift_id)
    return await out(session, s, user)


@router.post("", response_model=ShiftOut, response_model_by_alias=True, status_code=201)
async def publish(body: PublishIn, user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)), session: AsyncSession = DbSession):
    own_center = await service.center_of(session, user.unit_id)
    if user.role == rbac.MANAGER:
        if body.center_id and body.center_id != own_center:
            raise forbidden("Руководитель публикует смены только в своём центре")
        center = own_center
    else:
        if not body.center_id:
            raise validation("CENTER_REQUIRED", "Укажите центр", "centerId")
        center = body.center_id
    s = await service.publish_open(session, user, body.date, body.start_time, body.end_time, body.qualification, body.pay_preview, center)
    return await out(session, s, user)


@router.get("/team", response_model=Page[TeamShiftOut], response_model_by_alias=True)
async def team(user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)), session: AsyncSession = DbSession):
    """Руководитель видит все смены и обмены своего центра (без согласования); HR — все."""
    q = select(Shift).where(Shift.date >= clock.today()).order_by(Shift.date, Shift.start_time)
    if user.role == rbac.MANAGER:
        q = q.where(Shift.center_id == await service.center_of(session, user.unit_id))
    items = []
    for s in await session.scalars(q):
        events = await session.scalars(select(ShiftEvent).where(ShiftEvent.shift_id == s.id).order_by(ShiftEvent.at))
        history = []
        for e in events:
            actor = await session.get(Employee, e.actor_id) if e.actor_id else None
            history.append(ShiftEventOut(at=e.at, event=e.event, actor_name=actor.full_name if actor else None))
        items.append(TeamShiftOut(**(await out(session, s, user)).model_dump(), history=history))
    return Page(items=items)


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.include_router(router)


module = BackendModule(name="ext_shifts", feature="shifts", register=register, seed=seed, description="Биржа смен")
