"""Documentolog — mock документооборота. Все изменения кадровых данных уходят в 1С:ЗУП
документом (приказ на отпуск, заявление на аванс). Настоящий API подключается здесь."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.integrations.documentolog.models import Document


async def create_document(session: AsyncSession, kind: str, employee_id: str, data: dict[str, Any]) -> str:
    """Создаёт и сразу «регистрирует» документ (mock). Возвращает id документа."""
    doc = Document(
        id=new_id(),
        kind=kind,
        employee_id=employee_id,
        data=data,
        status="registered",
        external_number=f"DL-{clock.now():%Y}-{new_id()[:8].upper()}",
        created_at=clock.now(),
    )
    session.add(doc)
    await session.flush()
    return doc.id


__all__ = ["Document", "create_document"]
