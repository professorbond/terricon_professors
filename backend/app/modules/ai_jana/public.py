"""Публичный сервис AI Jana для других модулей (пробелы базы знаний): вопросы без ответа
(без идентификаторов сотрудников) и черновики/публикация документов базы."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import conflict, not_found
from app.core.ids import new_id
from app.modules.ai_jana.kb import invalidate
from app.modules.ai_jana.models import KbDoc, KbQuestion
from app.modules.ai_jana.text import terms

__all__ = ["KbDoc", "KbQuestion", "create_draft", "get_doc", "group_questions", "kb_corpus", "publish", "set_group", "terms", "update_draft"]


async def kb_corpus(session: AsyncSession, country: str) -> list[list[str]]:
    """Основы слов по разделам опубликованной базы страны — фон для IDF при группировке вопросов."""
    from app.modules.ai_jana.kb import split_sections

    docs = await session.scalars(select(KbDoc).where(KbDoc.country == country, KbDoc.status == "published"))
    return [terms(f"{d.title} {sec} {text}") for d in docs for sec, text in split_sections(d.body_md)]


async def group_questions(session: AsyncSession, group_id: str) -> list[KbQuestion]:
    q = select(KbQuestion).where(KbQuestion.gap_group_id == group_id).order_by(KbQuestion.asked_at.desc())
    return list(await session.scalars(q))


async def set_group(session: AsyncSession, question: KbQuestion, group_id: str) -> None:
    question.gap_group_id = group_id
    await session.flush()


async def get_doc(session: AsyncSession, doc_id: str) -> KbDoc:
    doc = await session.get(KbDoc, doc_id)
    if doc is None:
        raise not_found("Документ не найден")
    return doc


async def create_draft(session: AsyncSession, country: str, title: str, source_label: str, body_md: str) -> KbDoc:
    doc = KbDoc(
        id=f"kb-{country.lower()}-rule-{new_id()[:8]}", country=country, title=title, source_label=source_label,
        body_md=body_md, status="draft", updated_at=clock.now(),
    )
    session.add(doc)
    await session.flush()
    return doc


async def update_draft(session: AsyncSession, doc_id: str, title: str | None, source_label: str | None, body_md: str | None) -> KbDoc:
    doc = await get_doc(session, doc_id)
    if doc.status != "draft":
        raise conflict("NOT_A_DRAFT", "Опубликованный документ не редактируется здесь")
    if title is not None:
        doc.title = title
    if source_label is not None:
        doc.source_label = source_label
    if body_md is not None:
        doc.body_md = body_md
    doc.updated_at = clock.now()
    return doc


async def publish(session: AsyncSession, doc_id: str) -> KbDoc:
    """Публикует черновик — AI начинает отвечать по нему (индекс страны пересоберётся)."""
    doc = await get_doc(session, doc_id)
    doc.status, doc.updated_at = "published", clock.now()
    await session.flush()
    invalidate()
    return doc
