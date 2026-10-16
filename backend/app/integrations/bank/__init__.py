"""Банк-партнёр — mock выплат (всегда успех). Настоящий банк подключается здесь."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.ids import new_id
from app.integrations.bank.models import Payout


async def send_payout(session: AsyncSession, employee_id: str, amount: int, reference: str) -> str:
    payout = Payout(
        id=new_id(), employee_id=employee_id, amount=amount, reference=reference, status="paid", created_at=clock.now()
    )
    session.add(payout)
    await session.flush()
    return payout.id


__all__ = ["Payout", "send_payout"]
