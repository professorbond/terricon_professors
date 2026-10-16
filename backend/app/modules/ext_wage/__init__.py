"""«Зарплата по факту» — доступ к заработанному (CLAUDE.md §7.3). Флаг: wage_access."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.modules import BackendModule, ModuleContext
from app.core.org.models import Employee
from app.core.requests import RequestType
from app.modules.ext_wage.router import router
from app.modules.ext_wage.service import TYPE, summary

RU = {
    "request.type.wage_access": "Зарплата по факту",
    "notif.wage.paid.title": "Деньги отправлены",
    "notif.wage.paid.body": "{amount} отправлены на вашу карту",
}
KK = {
    "request.type.wage_access": "Нақты жалақы",
    "notif.wage.paid.title": "Ақша жіберілді",
    "notif.wage.paid.body": "{amount} картаңызға жіберілді",
}


async def contribute_profile(session: AsyncSession, viewer: Employee, employee: Employee) -> dict[str, Any]:
    """Доступная сумма — только самому сотруднику (это его деньги, другим не показываем)."""
    if viewer.id != employee.id:
        return {}
    return {"wage_access": await summary(session, employee)}


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    # Без согласующего: решение принимает система по правилам HR
    ctx.request_types.register(RequestType(code=TYPE, number_prefix="WA", title_key="request.type.wage_access", approver="none", cancellable=False))
    ctx.profile.register(contribute_profile)
    ctx.include_router(router)


module = BackendModule(name="ext_wage", feature="wage_access", register=register, description="Зарплата по факту")
