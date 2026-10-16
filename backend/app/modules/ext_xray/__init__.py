"""Рентген руководителей — аналитика HR-процессов, не оценка эффективности людей (CLAUDE.md §7.9). Флаг: xray.

Метрики за 90 дней по заявкам, где руководитель — согласующий: медианное время ответа, доля отказов,
решения позже срока, люди команды в зоне риска. HR видит всех; руководитель — только себя и перцентиль."""

from datetime import timedelta
from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, rbac
from app.core.db import DbSession
from app.core.modules import BackendModule, ModuleContext
from app.core.org.models import Employee, Unit
from app.core.org.service import list_team
from app.core.requests.models import OPEN_STATUSES, REJECTED, Request
from app.core.schemas import ApiModel, Page
from app.modules.ext_guarantees.policies import guarantee_for
from app.modules.ext_hr_console.public import employees_at_risk

WINDOW_DAYS = 90
router = APIRouter(prefix="/api/ext/hr/xray", tags=["ext: xray"])


class ManagerMetrics(ApiModel):
    manager_id: str
    manager_name: str
    department: str
    country: str
    team_size: int
    decided: int
    median_response_hours: float | None
    rejection_share: float | None  # 0..1
    late_decisions: int  # позже срока, или срок истёк и решила система / передано HR
    pending_now: int
    team_at_risk: int


class MyXray(ApiModel):
    metrics: ManagerMetrics
    peers: int
    slower_than_pct: int | None  # «вы отвечаете медленнее X% коллег»
    late_rank: int  # место по решениям позже срока (1 — больше всех)


async def metrics_for(session: AsyncSession, manager: Employee) -> ManagerMetrics:
    since = clock.now() - timedelta(days=WINDOW_DAYS)
    rows = list(
        await session.scalars(
            select(Request).where(Request.approver_id == manager.id, Request.approver_kind == "manager", Request.created_at >= since)
        )
    )
    by_manager = [r for r in rows if r.decided_by == manager.id and r.decided_at]
    hours = [(r.decided_at - r.created_at).total_seconds() / 3600 for r in by_manager]
    late = 0
    for r in rows:
        g = await guarantee_for(session, r.id)
        if g is None:
            continue
        if (r.decided_at and r.decided_at > g.deadline_at) or g.resolution in ("auto_approved", "escalated"):
            late += 1
    team = await list_team(session, manager.id)
    unit = await session.get(Unit, manager.unit_id)
    return ManagerMetrics(
        manager_id=manager.id,
        manager_name=manager.full_name,
        department=unit.name if unit else "—",
        country=manager.country,
        team_size=len(team),
        decided=len(by_manager),
        median_response_hours=round(median(hours), 1) if hours else None,
        rejection_share=round(sum(r.status == REJECTED for r in by_manager) / len(by_manager), 2) if by_manager else None,
        late_decisions=late,
        pending_now=sum(r.status in OPEN_STATUSES for r in rows),
        team_at_risk=len(await employees_at_risk(session, [e.id for e in team])),
    )


async def all_metrics(session: AsyncSession, country: str | None = None) -> list[ManagerMetrics]:
    q = select(Employee).where(Employee.role == rbac.MANAGER, Employee.active)
    if country:
        q = q.where(Employee.country == country)
    items = [await metrics_for(session, m) for m in await session.scalars(q)]
    items.sort(key=lambda m: (-m.late_decisions, -(m.median_response_hours or 0), m.manager_name))
    return items


@router.get("", response_model=Page[ManagerMetrics], response_model_by_alias=True)
async def xray(country: str | None = None, user: Employee = Depends(rbac.require_role(rbac.HR)), session: AsyncSession = DbSession):
    """Все руководители, сначала — с наибольшим числом решений позже срока."""
    return Page(items=await all_metrics(session, country))


@router.get("/me", response_model=MyXray, response_model_by_alias=True)
async def xray_me(user: Employee = Depends(rbac.require_role(rbac.MANAGER)), session: AsyncSession = DbSession):
    """Руководитель видит только свои метрики и своё место среди коллег — без чужих имён и цифр."""
    everyone = await all_metrics(session)
    mine = next(m for m in everyone if m.manager_id == user.id)
    peers = [m for m in everyone if m.manager_id != user.id]
    timed = [m for m in peers if m.median_response_hours is not None]
    slower = None
    if mine.median_response_hours is not None and timed:
        slower = round(100 * sum(m.median_response_hours < mine.median_response_hours for m in timed) / len(timed))
    rank = 1 + sum(m.late_decisions > mine.late_decisions for m in peers)
    return MyXray(metrics=mine, peers=len(peers), slower_than_pct=slower, late_rank=rank)


def register(ctx: ModuleContext) -> None:
    ctx.include_router(router)


module = BackendModule(name="ext_xray", feature="xray", register=register, description="Рентген руководителей")
