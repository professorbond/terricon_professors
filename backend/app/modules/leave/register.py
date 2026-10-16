from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import validation
from app.core.modules import ModuleContext
from app.core.org.models import Employee
from app.core.profile import LeaveBalance
from app.core.requests import RequestType
from app.core.requests import service as requests
from app.core.requests.models import APPROVED, Request
from app.integrations.documentolog import Document, create_document
from app.modules.leave.router import router
from app.modules.leave.service import TYPE, balance

RU = {
    "request.type.vacation": "Отпуск",
    "document.leave_order": "Приказ на отпуск",
}
KK = {
    "request.type.vacation": "Демалыс",
    "document.leave_order": "Демалыс туралы бұйрық",
}


async def recheck_balance(session: AsyncSession, request: Request, decision: str, **_: object) -> None:
    """Остаток мог измениться с момента подачи — проверяем ещё раз при одобрении."""
    if request.type != TYPE or decision != APPROVED:
        return
    owner = await session.get(Employee, request.employee_id)
    assert owner is not None
    days = (await balance(session, owner))["days"]
    if request.payload["requestedDays"] > days:
        raise validation("INSUFFICIENT_BALANCE", f"У сотрудника осталось {days} дн.", data={"available": days})


async def send_order(session: AsyncSession, request: Request, **_: object) -> None:
    """Одобренный отпуск → приказ в Documentolog → 1С:ЗУП (официальные данные напрямую не правим)."""
    if request.type != TYPE or request.status != APPROVED:
        return
    doc_id = await create_document(
        session,
        "leave_order",
        request.employee_id,
        {
            "requestId": request.id,
            "startDate": request.payload["startDate"],
            "endDate": request.payload["endDate"],
            "days": request.payload["requestedDays"],
        },
    )
    doc = await session.get(Document, doc_id)
    assert doc is not None
    await requests.add_note(
        session,
        request,
        "document_registered",
        {"documentId": doc_id, "documentKind": "leave_order", "documentNumber": doc.external_number},
    )


async def contribute_profile(session: AsyncSession, viewer: Employee, employee: Employee) -> dict[str, Any]:
    return {"leave_balance": LeaveBalance(**await balance(session, employee))}


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.request_types.register(
        RequestType(code=TYPE, number_prefix="JL", title_key="request.type.vacation", approver="manager")
    )
    ctx.events.subscribe("request.before_decision", recheck_balance)
    ctx.events.subscribe("request.decided", send_order)
    ctx.profile.register(contribute_profile)
    ctx.include_router(router)
