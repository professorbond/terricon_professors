"""Пробелы базы знаний: AI учится на своих «не знаю» через HR (CLAUDE.md §7.10). Флаг: kb_gaps.

AI ничего не публикует сам: черновик правила готовит LLM (или пустой шаблон), HR правит и публикует."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.db import DbSession
from app.core.errors import not_found
from app.core.modules import BackendModule, ModuleContext
from app.core.org.models import Employee
from app.core.schemas import ApiModel
from app.integrations import llm
from app.modules.ai_jana import public as ai
from app.modules.ext_kb_gaps.grouping import assign
from app.modules.ext_kb_gaps.models import KbGapGroup
from app.modules.ext_kb_gaps.seed import seed

router = APIRouter(prefix="/api/ext/kb", tags=["ext: kb gaps"])
HR_ONLY = Depends(rbac.require_role(rbac.HR))
RULE_SOURCE = "Внутреннее правило Jana Post (утверждено HR)"

DRAFT_PROMPT = """Ты помогаешь HR компании Jana Post закрыть пробел в базе знаний. Сотрудники задавали вопросы,
на которые в базе нет ответа. Напиши ЧЕРНОВИК внутреннего правила в markdown: 2–3 раздела с заголовками «## …»,
коротко и простым языком. Не придумывай цифры, сроки и суммы — вместо них ставь [указать]. HR проверит и заполнит.
Отвечай только текстом правила, без вступления."""


class GapOut(ApiModel):
    id: str
    country: str
    label: str
    count: int
    samples: list[str]  # формулировки вопросов — без имён и идентификаторов
    status: str
    draft_doc_id: str | None
    last_asked_at: datetime


class DocOut(ApiModel):
    id: str
    country: str
    title: str
    source_label: str
    body_md: str
    status: str
    updated_at: datetime


class DocUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    source_label: str | None = Field(default=None, min_length=3, max_length=300)
    body_md: str | None = Field(default=None, min_length=10)


async def gap_out(session: AsyncSession, g: KbGapGroup) -> GapOut:
    qs = await ai.group_questions(session, g.id)
    samples = list(dict.fromkeys(q.question for q in qs))[:5]
    return GapOut(
        id=g.id, country=g.country, label=g.label, count=g.question_count, samples=samples,
        status=g.status, draft_doc_id=g.draft_doc_id, last_asked_at=g.last_asked_at,
    )


def doc_out(d: ai.KbDoc) -> DocOut:
    return DocOut(id=d.id, country=d.country, title=d.title, source_label=d.source_label, body_md=d.body_md, status=d.status, updated_at=d.updated_at)


@router.get("/gaps", response_model=list[GapOut], response_model_by_alias=True)
async def gaps(country: str | None = None, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    """«23 вопроса: оплата ночных смен (KZ)» — сначала самые частые."""
    q = select(KbGapGroup).order_by(KbGapGroup.question_count.desc(), KbGapGroup.last_asked_at.desc())
    if country:
        q = q.where(KbGapGroup.country == country)
    return [await gap_out(session, g) for g in await session.scalars(q)]


async def _group(session: AsyncSession, gap_id: str) -> KbGapGroup:
    g = await session.get(KbGapGroup, gap_id)
    if g is None:
        raise not_found("Группа вопросов не найдена")
    return g


@router.post("/gaps/{gap_id}/draft", response_model=DocOut, response_model_by_alias=True)
async def draft(gap_id: str, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    """Подготовить черновик правила. С LLM — по вопросам сотрудников; без LLM — пустой шаблон."""
    g = await _group(session, gap_id)
    if g.draft_doc_id:
        return doc_out(await ai.get_doc(session, g.draft_doc_id))
    samples = (await gap_out(session, g)).samples
    body = await llm.complete(DRAFT_PROMPT, [{"role": "user", "content": "Вопросы сотрудников:\n- " + "\n- ".join(samples)}])
    if not body:
        body = f"## {g.label}\n[Опишите правило: кого касается, сколько, в какие сроки.]\n\n## Как оформить\n[Куда обращаться и какие документы нужны.]"
    doc = await ai.create_draft(session, g.country, g.label.rstrip("?"), RULE_SOURCE, body)
    g.status, g.draft_doc_id = "drafted", doc.id
    return doc_out(doc)


@router.get("/docs/{doc_id}", response_model=DocOut, response_model_by_alias=True)
async def get_doc(doc_id: str, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    return doc_out(await ai.get_doc(session, doc_id))


@router.put("/docs/{doc_id}", response_model=DocOut, response_model_by_alias=True)
async def update_doc(doc_id: str, body: DocUpdate, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    return doc_out(await ai.update_draft(session, doc_id, body.title, body.source_label, body.body_md))


@router.post("/docs/{doc_id}/publish", response_model=DocOut, response_model_by_alias=True)
async def publish(doc_id: str, user: Employee = HR_ONLY, session: AsyncSession = DbSession):
    """Публикация человеком: документ попадает в базу страны, AI начинает по нему отвечать."""
    doc = await ai.publish(session, doc_id)
    for g in await session.scalars(select(KbGapGroup).where(KbGapGroup.draft_doc_id == doc_id)):
        g.status = "published"
    return doc_out(doc)


async def on_unanswered(session: AsyncSession, question: Any, **_: Any) -> None:
    await assign(session, question)


def register(ctx: ModuleContext) -> None:
    ctx.events.subscribe("ai.unanswered", on_unanswered)
    ctx.include_router(router)


module = BackendModule(name="ext_kb_gaps", feature="kb_gaps", register=register, seed=seed, description="Пробелы базы знаний")
