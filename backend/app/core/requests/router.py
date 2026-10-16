"""Общий API заявок. Создание — в эндпоинте модуля типа (у каждого типа своя форма)."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.i18n import t
from app.core.org.models import Employee
from app.core.requests import service
from app.core.requests.registry import request_types
from app.core.requests.schemas import RequestOut, present
from app.core.schemas import ApiModel, Page

router = APIRouter(prefix="/api/requests", tags=["requests"])


class DecideIn(ApiModel):
    decision: Literal["Approved", "Rejected"]
    expected_version: int | None = None
    reason_code: str | None = None
    comment: str | None = None


class RequestTypeOut(ApiModel):
    code: str
    title: str
    approver: str
    cancellable: bool


async def _page(session: AsyncSession, rows: list, viewer: Employee) -> Page[RequestOut]:
    return Page(items=[await present(session, r, viewer) for r in rows])


@router.get("/types", response_model=list[RequestTypeOut], response_model_by_alias=True)
async def list_types(user: Employee = Depends(current_user)) -> list[RequestTypeOut]:
    return [
        RequestTypeOut(code=rt.code, title=t(rt.title_key, user.lang), approver=rt.approver, cancellable=rt.cancellable)
        for rt in request_types.all()
    ]


@router.get("/my", response_model=Page[RequestOut], response_model_by_alias=True)
async def my_requests(
    type: str | None = None,
    status: str | None = None,
    user: Employee = Depends(current_user),
    session: AsyncSession = DbSession,
) -> Page[RequestOut]:
    return await _page(session, await service.list_mine(session, user, type, status), user)


@router.get("/inbox", response_model=Page[RequestOut], response_model_by_alias=True)
async def inbox(
    status: Literal["open", "all"] = "open",
    type: str | None = None,
    user: Employee = Depends(rbac.require_role(rbac.MANAGER, rbac.HR)),
    session: AsyncSession = DbSession,
) -> Page[RequestOut]:
    rows = await service.list_inbox(session, user, only_open=status == "open", type_code=type)
    return await _page(session, rows, user)


@router.get("/all", response_model=Page[RequestOut], response_model_by_alias=True)
async def registry(
    type: str | None = None,
    status: str | None = None,
    country: str | None = None,
    unit_id: str | None = Query(default=None, alias="unitId"),
    created_from: date | None = Query(default=None, alias="from"),
    created_to: date | None = Query(default=None, alias="to"),
    user: Employee = Depends(rbac.require_role(rbac.HR)),
    session: AsyncSession = DbSession,
) -> Page[RequestOut]:
    """Реестр всех заявок для HR с фильтрами."""
    rows = await service.list_all(session, type, status, country, unit_id, created_from, created_to)
    return await _page(session, rows, user)


@router.get("/{request_id}", response_model=RequestOut, response_model_by_alias=True)
async def get_request(
    request_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession
) -> RequestOut:
    return await present(session, await service.get_visible(session, user, request_id), user)


@router.post("/{request_id}/decide", response_model=RequestOut, response_model_by_alias=True)
async def decide(
    request_id: str,
    body: DecideIn,
    user: Employee = Depends(current_user),
    session: AsyncSession = DbSession,
) -> RequestOut:
    req = await service.decide(
        session, user, request_id, body.decision, body.expected_version, body.reason_code, body.comment
    )
    return await present(session, req, user)


@router.post("/{request_id}/cancel", response_model=RequestOut, response_model_by_alias=True)
async def cancel(
    request_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession
) -> RequestOut:
    return await present(session, await service.cancel(session, user, request_id), user)
