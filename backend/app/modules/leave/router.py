from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import not_found
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.core.requests.models import SUBMITTED
from app.core.requests.schemas import present
from app.core.schemas import Page
from app.modules.leave.schemas import (
    LeaveBalanceOut,
    LeaveDecisionIn,
    LeaveEventOut,
    LeaveRequestOut,
    SubmitLeaveIn,
)
from app.modules.leave.service import TYPE, balance, validate_new

router = APIRouter(prefix="/api/leave", tags=["leave"])


async def to_leave(session: AsyncSession, req, viewer: Employee) -> LeaveRequestOut:
    r = await present(session, req, viewer)
    return LeaveRequestOut(
        id=r.id,
        number=r.number,
        submission_key=r.submission_key,
        employee_id=r.employee_id or "",
        employee_name=r.employee_name or "",
        manager_id=r.approver_id,
        manager_name=r.approver_name,
        start_date=date.fromisoformat(r.payload["startDate"]),
        end_date=date.fromisoformat(r.payload["endDate"]),
        requested_days=r.payload["requestedDays"],
        comment=r.payload.get("comment", ""),
        status=r.status,
        created_at=r.created_at,
        version=r.version,
        history=[
            LeaveEventOut(
                id=e.id,
                status=e.status,
                occurred_at=e.occurred_at,
                actor_label=e.actor_label,
                actor_id=e.actor_id,
                comment=e.comment,
                event=e.event,
            )
            for e in r.history
        ],
        decision_comment=r.decision_comment,
        decision_reason_code=r.decision_reason_code,
        decided_by_system=r.decided_by_system,
        permissions=r.permissions,
    )


async def _page(session: AsyncSession, rows, viewer: Employee) -> Page[LeaveRequestOut]:
    return Page(items=[await to_leave(session, r, viewer) for r in rows])


@router.get("/balance", response_model=LeaveBalanceOut, response_model_by_alias=True)
async def my_balance(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    days, as_of = await balance(session, user)
    pending = sum(
        r.payload["requestedDays"] for r in await requests.list_mine(session, user, TYPE) if r.status == SUBMITTED
    )
    return LeaveBalanceOut(days=days, as_of=as_of, pending_days=pending)


@router.get("/requests/my", response_model=Page[LeaveRequestOut], response_model_by_alias=True)
async def list_mine(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await _page(session, await requests.list_mine(session, user, TYPE), user)


@router.get("/requests/pending", response_model=Page[LeaveRequestOut], response_model_by_alias=True)
async def list_pending(
    user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)), session: AsyncSession = DbSession
):
    """Очередь согласования: открытые заявки, где пользователь — согласующий."""
    return await _page(session, await requests.list_inbox(session, user, True, TYPE), user)


@router.get("/requests/team", response_model=Page[LeaveRequestOut], response_model_by_alias=True)
async def list_team(
    user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)), session: AsyncSession = DbSession
):
    """Все заявки команды (любой статус). Для HR — все заявки на отпуск."""
    if user.role == rbac.HR:
        rows = await requests.list_all(session, TYPE)
    else:
        rows = await requests.list_inbox(session, user, False, TYPE)
    return await _page(session, rows, user)


@router.get("/requests/{request_id}", response_model=LeaveRequestOut, response_model_by_alias=True)
async def get_one(request_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    req = await requests.get_visible(session, user, request_id)
    if req.type != TYPE:
        raise not_found("Заявка на отпуск не найдена")
    return await to_leave(session, req, user)


@router.post("/requests", response_model=LeaveRequestOut, response_model_by_alias=True, status_code=201)
async def submit(body: SubmitLeaveIn, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    await requests.lock_employee(session, user.id)
    existing = await requests.find_by_submission_key(session, user, body.submission_key)
    if existing is not None and existing.type == TYPE:  # повтор той же отправки
        return await to_leave(session, existing, user)
    days = await validate_new(session, user, body.start_date, body.end_date)
    payload = {
        "startDate": body.start_date.isoformat(),
        "endDate": body.end_date.isoformat(),
        "requestedDays": days,
        "comment": body.comment.strip(),
    }
    req = await requests.create(session, user, TYPE, payload, body.submission_key)
    return await to_leave(session, req, user)


@router.post("/requests/{request_id}/decision", response_model=LeaveRequestOut, response_model_by_alias=True)
async def decide(
    request_id: str,
    body: LeaveDecisionIn,
    user: Employee = Depends(current_user),
    session: AsyncSession = DbSession,
):
    req = await requests.get_visible(session, user, request_id)
    if req.type != TYPE:
        raise not_found("Заявка на отпуск не найдена")
    req = await requests.decide(
        session, user, request_id, body.decision, body.expected_version, body.reason_code, body.comment
    )
    return await to_leave(session, req, user)
