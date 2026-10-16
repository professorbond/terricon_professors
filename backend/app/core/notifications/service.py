from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.core.notifications.models import Notification


async def notify(
    session: AsyncSession,
    employee_id: str,
    kind: str,
    title_key: str,
    body_key: str,
    params: dict[str, Any] | None = None,
    target: dict[str, Any] | None = None,
    link: str | None = None,
) -> Notification:
    """Создать уведомление. Тексты — ключи i18n (app.core.i18n), рендерятся на языке получателя."""
    n = Notification(
        id=new_id(),
        employee_id=employee_id,
        kind=kind,
        title_key=title_key,
        body_key=body_key,
        params=params or {},
        target=target,
        link=link,
        created_at=clock.now(),
    )
    session.add(n)
    await session.flush()
    return n


async def unread_count(session: AsyncSession, employee_id: str) -> int:
    q = select(func.count()).select_from(Notification).where(
        Notification.employee_id == employee_id, Notification.read_at.is_(None)
    )
    return int((await session.scalar(q)) or 0)
