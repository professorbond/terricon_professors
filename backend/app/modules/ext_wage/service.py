"""Расчёт и вывод «Зарплаты по факту» (CLAUDE.md §7.3). Это не кредит: только отработанные смены из табеля."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import validation
from app.core.ids import new_id
from app.core.notifications import notify
from app.core.org.models import Employee
from app.core.requests import service as requests
from app.integrations import bank, documentolog
from app.integrations.documentolog import Document
from app.integrations.zup import get_zup
from app.modules.ext_guarantees.policies import setting
from app.modules.ext_wage.models import Withdrawal
from app.modules.ext_wage.schemas import PayslipExplained, PayslipLine, WageSummary

TYPE = "wage_access"
CURRENCY = {"KZ": "KZT", "KG": "KGS"}
SYMBOL = {"KZ": "₸", "KG": "сом"}
# Демонстрационные ставки удержаний (не налоговая консультация)
DEMO_TAX = {
    "KZ": [("OPV", "ОПВ (пенсионные взносы) 10%", 0.10), ("VOSMS", "ВОСМС 2%", 0.02), ("IPN", "ИПН 10%", 0.10)],
    "KG": [("PF", "Пенсионный фонд 10%", 0.10), ("PN", "Подоходный налог 10%", 0.10)],
}


def period_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def bounds(period: str) -> tuple[date, date]:
    year, month = map(int, period.split("-"))
    start = date(year, month, 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return start, end


async def earned_for(session: AsyncSession, employee: Employee, period: str) -> tuple[int, int, int, int]:
    """(заработано, смен, ночных, план смен) по табелю 1С:ЗУП за период до сегодняшнего дня."""
    zup = get_zup()
    salary = await zup.get_salary(session, employee.id)
    attrs = await zup.get_hr_attrs(session, employee.id)
    start, end = bounds(period)
    sheet = await zup.get_timesheet(session, employee.id, start, min(end, clock.today()))
    planned = attrs.planned_shifts_per_month if attrs else 22
    shifts, nights = len(sheet), sum(1 for e in sheet if e.shift_type == "night")
    if salary is None:
        return 0, shifts, nights, planned
    if salary.shift_rate:
        earned = shifts * salary.shift_rate + nights * (salary.night_bonus_rate or 0)
    else:
        earned = salary.monthly_base * shifts // planned if planned else 0
    return earned, shifts, nights, planned


async def withdrawals(session: AsyncSession, employee_id: str, period: str) -> list[Withdrawal]:
    q = select(Withdrawal).where(
        Withdrawal.employee_id == employee_id, Withdrawal.period == period, Withdrawal.status.in_(("paid", "pending"))
    )
    return list(await session.scalars(q))


async def summary(session: AsyncSession, employee: Employee) -> WageSummary:
    period = period_of(clock.today())
    earned, shifts, nights, planned = await earned_for(session, employee, period)
    limit = await setting(session, employee.country, TYPE, "wage_limit_pct")
    max_per = await setting(session, employee.country, TYPE, "wage_max_per_period")
    min_amount = await setting(session, employee.country, TYPE, "wage_min_amount")
    done = await withdrawals(session, employee.id, period)
    withdrawn = sum(w.amount for w in done)
    return WageSummary(
        period=period,
        currency=CURRENCY.get(employee.country, "KZT"),
        shifts_worked=shifts,
        night_shifts=nights,
        shifts_planned=planned,
        earned=earned,
        limit_pct=limit,
        withdrawn=withdrawn,
        available=max(0, earned * limit // 100 - withdrawn),
        withdrawals_left=max(0, max_per - len(done)),
        min_amount=min_amount,
        max_per_period=max_per,
    )


async def withdraw(session: AsyncSession, employee: Employee, amount: int) -> tuple[Withdrawal, str, str]:
    await requests.lock_employee(session, employee.id)  # двойной клик не даст двух выплат
    s = await summary(session, employee)
    if s.withdrawals_left <= 0:
        raise validation("LIMIT_PER_PERIOD", f"В этом месяце можно не больше {s.max_per_period} раз", "amount", {"maxPerPeriod": s.max_per_period})
    if amount < s.min_amount:
        raise validation("BELOW_MIN_AMOUNT", f"Минимальная сумма — {s.min_amount}", "amount", {"minAmount": s.min_amount})
    if amount > s.available:
        raise validation("AMOUNT_EXCEEDS_AVAILABLE", f"Доступно {s.available}", "amount", {"available": s.available})

    # Заявка без согласующего → одобрена системой (это уже заработанные деньги)
    req = await requests.create(session, employee, TYPE, {"amount": amount, "period": s.period, "currency": s.currency})
    await requests.decide_by_system(session, req.id, "Approved", "Заработанные деньги: лимит и табель проверены автоматически", "WAGE_AUTO")
    doc_id = await documentolog.create_document(
        session, "wage_advance", employee.id, {"requestId": req.id, "amount": amount, "period": s.period}
    )
    doc = await session.get(Document, doc_id)
    assert doc is not None
    payout_id = await bank.send_payout(session, employee.id, amount, f"wage-access:{req.number}")
    w = Withdrawal(
        id=new_id(), employee_id=employee.id, period=s.period, amount=amount, request_id=req.id,
        document_id=doc_id, payout_id=payout_id, status="paid", created_at=clock.now(),
    )
    session.add(w)
    await requests.add_note(
        session, req, "document_registered",
        {"documentId": doc_id, "documentKind": "wage_advance", "documentNumber": doc.external_number},
    )
    await requests.add_note(session, req, "payout_sent", {"payoutId": payout_id, "amount": amount})
    await notify(
        session, employee.id, "wage.paid", "notif.wage.paid.title", "notif.wage.paid.body",
        {"amount": money(amount, employee.country)}, {"kind": "request", "requestId": req.id},
    )
    await session.flush()
    return w, req.number, doc.external_number


def money(amount: int, country: str) -> str:
    return f"{amount:,}".replace(",", " ") + " " + SYMBOL.get(country, "₸")


async def payslip(session: AsyncSession, employee: Employee, period: str) -> PayslipExplained:
    earned, shifts, nights, planned = await earned_for(session, employee, period)
    salary = await get_zup().get_salary(session, employee.id)
    lines: list[PayslipLine] = []
    if salary and salary.shift_rate:
        lines.append(PayslipLine(code="SHIFTS", label=f"Смены: {shifts} × {money(salary.shift_rate, employee.country)}", amount=shifts * salary.shift_rate))
        if nights:
            lines.append(PayslipLine(code="NIGHT", label=f"Ночные: {nights} × {money(salary.night_bonus_rate or 0, employee.country)}", amount=nights * (salary.night_bonus_rate or 0)))
    else:
        lines.append(PayslipLine(code="BASE", label=f"Оклад за {shifts} из {planned} смен", amount=earned))
    gross = earned
    base = gross
    for code, label, rate in DEMO_TAX.get(employee.country, []):
        value = round(base * rate)
        lines.append(PayslipLine(code=code, label=label, amount=-value))
        if code in ("OPV", "VOSMS", "PF"):
            base -= value  # подоходный считается после взносов
    net = gross + sum(line.amount for line in lines if line.amount < 0)
    received = sum(w.amount for w in await withdrawals(session, employee.id, period))
    return PayslipExplained(
        period=period,
        currency=CURRENCY.get(employee.country, "KZT"),
        lines=lines,
        gross=gross,
        net=net,
        already_received=received,
        to_be_paid=max(0, net - received),
        note=f"Уже получено по факту: {money(received, employee.country)} — будет учтено в день зарплаты, "
        f"к выплате останется {money(max(0, net - received), employee.country)}. Ставки удержаний демонстрационные.",
    )
