import re

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import validation
from app.core.org.models import Employee
from app.modules.ext_wage import service
from app.modules.ext_wage.schemas import PayslipExplained, WageSummary, WithdrawIn, WithdrawOut

router = APIRouter(prefix="/api/ext/wage", tags=["ext: wage access"])


@router.get("/summary", response_model=WageSummary, response_model_by_alias=True)
async def summary(user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return await service.summary(session, user)


@router.post("/withdraw", response_model=WithdrawOut, response_model_by_alias=True, status_code=201)
async def withdraw(body: WithdrawIn, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    w, number, doc_number = await service.withdraw(session, user, body.amount)
    return WithdrawOut(
        request_id=w.request_id, request_number=number, amount=w.amount, document_number=doc_number,
        payout_id=w.payout_id or "", summary=await service.summary(session, user),
    )


@router.get("/payslip-explained", response_model=PayslipExplained, response_model_by_alias=True)
async def payslip(period: str | None = None, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    period = period or service.period_of(clock.today())
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
        raise validation("INVALID_PERIOD", "Период в формате ГГГГ-ММ", "period")
    return await service.payslip(session, user, period)
