from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, rbac
from app.core.db import DbSession
from app.core.errors import conflict, not_found
from app.core.i18n import t
from app.core.ids import new_id
from app.core.notifications import notify
from app.core.org.models import Employee, Unit
from app.core.schemas import Page
from app.modules.ext_guarantees.policies import country_setting
from app.modules.ext_hr_console.models import RiskSignal, SalaryReview
from app.modules.ext_hr_console.reviews import proposed_review_date
from app.modules.ext_hr_console.schemas import RiskCard, SavingsOut, SignalOut
from app.modules.ext_hr_console.signals import recalculate

router = APIRouter(prefix="/api/ext/hr", tags=["ext: hr console"])
HR_ONLY = Depends(rbac.require_role(rbac.HR))
CURRENCY = {"KZ": ("KZT", "₸"), "KG": ("KGS", "сом")}
REVIEW_IN_DAYS = 14


def money(amount: int, country: str) -> str:
    return f"{amount:,}".replace(",", " ") + " " + CURRENCY.get(country, ("", "₸"))[1]


def signal_out(s: RiskSignal, country: str, lang: str) -> SignalOut:
    params = dict(s.details)
    for key in ("offer", "salary"):
        if key in params:
            params[key] = money(params[key], country)
    return SignalOut(
        id=s.id, kind=s.kind, title=t(f"risk.{s.kind}", lang, params), details=s.details, detected_at=s.detected_at,
        status=s.status, action=s.action, actioned_at=s.actioned_at, retained_confirmed=s.retained_confirmed,
    )


async def card(session: AsyncSession, emp: Employee, signals: list[RiskSignal], lang: str) -> RiskCard:
    unit = await session.get(Unit, emp.unit_id)
    manager = await session.get(Employee, emp.manager_id) if emp.manager_id else None
    return RiskCard(
        employee_id=emp.id, employee_name=emp.full_name, position=emp.position, department=unit.name if unit else "—",
        country=emp.country, manager_name=manager.full_name if manager else None,
        open_signals=sum(1 for s in signals if s.status == "open"),
        signals=[signal_out(s, emp.country, lang) for s in signals],
        next_review_date=await proposed_review_date(session, emp.id),
    )


@router.get("/risks", response_model=Page[RiskCard], response_model_by_alias=True)
async def risks(country: str | None = None, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    """Радар: сотрудники с открытыми или обработанными сигналами, сначала — с наибольшим числом причин."""
    q = select(RiskSignal, Employee).join(Employee, Employee.id == RiskSignal.employee_id).where(RiskSignal.status != "resolved")
    if country:
        q = q.where(Employee.country == country)
    by_emp: dict[str, tuple[Employee, list[RiskSignal]]] = {}
    for signal, emp in (await session.execute(q.order_by(RiskSignal.detected_at))).all():
        by_emp.setdefault(emp.id, (emp, []))[1].append(signal)
    cards = [await card(session, emp, sigs, user.lang) for emp, sigs in by_emp.values()]
    cards.sort(key=lambda c: (-c.open_signals, -len(c.signals), c.employee_name))
    return Page(items=cards)


async def _signal(session: AsyncSession, signal_id: str) -> tuple[RiskSignal, Employee]:
    s = await session.get(RiskSignal, signal_id)
    if s is None:
        raise not_found("Сигнал не найден")
    emp = await session.get(Employee, s.employee_id)
    assert emp is not None
    return s, emp


@router.post("/risks/{signal_id}/propose-review", response_model=RiskCard, response_model_by_alias=True)
async def propose_review(signal_id: str, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    """«Предложить пересмотр» → пересмотр зарплаты, уведомление сотруднику, сигнал обработан."""
    s, emp = await _signal(session, signal_id)
    if s.status == "resolved":
        raise conflict("SIGNAL_RESOLVED", "Сигнал уже закрыт")
    review_date = clock.today() + timedelta(days=REVIEW_IN_DAYS)
    session.add(SalaryReview(id=new_id(), employee_id=emp.id, proposed_by=user.id, proposed_at=clock.now(), review_date=review_date, source_signal_id=s.id))
    s.status, s.action, s.actioned_at = "actioned", "propose_review", clock.now()
    await notify(
        session, emp.id, "salary.review", "notif.salary_review.title", "notif.salary_review.body",
        {"date": review_date.strftime("%d.%m.%Y")}, None, None,
    )
    await session.flush()
    signals = list(await session.scalars(select(RiskSignal).where(RiskSignal.employee_id == emp.id, RiskSignal.status != "resolved")))
    return await card(session, emp, signals, user.lang)


@router.post("/risks/{signal_id}/confirm-retained", response_model=SignalOut, response_model_by_alias=True)
async def confirm_retained(signal_id: str, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    """«Сотрудник остался» — попадает в счётчик сохранённых денег."""
    s, emp = await _signal(session, signal_id)
    s.retained_confirmed = True
    if s.status == "open":
        s.status, s.actioned_at = "actioned", clock.now()
    s.action = s.action or "retained"
    return signal_out(s, emp.country, user.lang)


@router.post("/risks/recalculate", response_model=Page[RiskCard], response_model_by_alias=True)
async def recalc(country: str | None = None, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    await recalculate(session, clock.now())
    return await risks(country, user, session)


@router.get("/savings", response_model=SavingsOut, response_model_by_alias=True)
async def savings(country: str | None = None, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    country = country or user.country
    retained = len(
        list(
            await session.scalars(
                select(RiskSignal.employee_id)
                .join(Employee, Employee.id == RiskSignal.employee_id)
                .where(RiskSignal.retained_confirmed, Employee.country == country)
            )
        )
    )
    avg = await country_setting(session, country, "avg_annual_salary")
    pct = await country_setting(session, country, "replacement_cost_pct")
    per_person = avg * pct // 100
    return SavingsOut(
        country=country, currency=CURRENCY.get(country, ("KZT", "₸"))[0], retained_count=retained,
        per_person=per_person, saved=retained * per_person,
        formula=f"{retained} × {money(avg, country)} × {pct}% = {money(retained * per_person, country)}",
    )
