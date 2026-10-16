from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import not_found
from app.core.i18n import t
from app.core.notifications.models import Notification
from app.core.notifications.service import unread_count
from app.core.org.models import Employee
from app.core.schemas import ApiModel, Page

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationOut(ApiModel):
    id: str
    user_id: str
    kind: str
    title: str
    message: str
    created_at: datetime
    read_at: datetime | None
    target: dict[str, Any] | None
    link: str | None
    # Ключи i18n и параметры — фронтенд может перевести сам (title/message уже переведены)
    title_key: str
    body_key: str
    params: dict[str, Any]


class UnreadCount(ApiModel):
    unread: int


def present(n: Notification, lang: str) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        user_id=n.employee_id,
        kind=n.kind,
        title=t(n.title_key, lang, n.params),
        message=t(n.body_key, lang, n.params),
        created_at=n.created_at,
        read_at=n.read_at,
        target=n.target,
        link=n.link,
        title_key=n.title_key,
        body_key=n.body_key,
        params=n.params,
    )


@router.get("", response_model=Page[NotificationOut], response_model_by_alias=True)
async def list_mine(
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    user: Employee = Depends(current_user),
    session: AsyncSession = DbSession,
) -> Page[NotificationOut]:
    q = select(Notification).where(Notification.employee_id == user.id)
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    rows = await session.scalars(q.order_by(Notification.created_at.desc()).limit(200))
    return Page(items=[present(n, user.lang) for n in rows])


@router.get("/unread-count", response_model=UnreadCount, response_model_by_alias=True)
async def get_unread_count(
    user: Employee = Depends(current_user), session: AsyncSession = DbSession
) -> UnreadCount:
    return UnreadCount(unread=await unread_count(session, user.id))


@router.post("/{notification_id}/read", response_model=NotificationOut, response_model_by_alias=True)
async def mark_read(
    notification_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession
) -> NotificationOut:
    n = await session.get(Notification, notification_id)
    # Чужое уведомление неотличимо от несуществующего
    if n is None or n.employee_id != user.id:
        raise not_found("Уведомление не найдено")
    if n.read_at is None:
        n.read_at = clock.now()
    return present(n, user.lang)


@router.post("/read-all", response_model=UnreadCount, response_model_by_alias=True)
async def mark_all_read(
    user: Employee = Depends(current_user), session: AsyncSession = DbSession
) -> UnreadCount:
    await session.execute(
        update(Notification)
        .where(Notification.employee_id == user.id, Notification.read_at.is_(None))
        .values(read_at=clock.now())
    )
    return UnreadCount(unread=0)
