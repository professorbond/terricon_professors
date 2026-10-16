"""ЗАГЛУШКА этапа 1 (заменяется на этапе 3). Ответы помечены заголовком X-Stub: true."""

from datetime import datetime

from fastapi import APIRouter, Depends, Response

from app.core.auth import current_user
from app.core.org.models import Employee
from app.modules.ai_jana.schemas import AskIn, AskOut, KnowledgeArticle, KnowledgeSource

router = APIRouter(prefix="/api/ai", tags=["ai_jana (stub)"])

SRC = KnowledgeSource(
    article_id="kb-kz-leave",
    title="Ежегодный оплачиваемый отпуск",
    section="Продолжительность",
    updated_at=datetime(2026, 9, 1),
    source_label="ТК РК, ст. 88 (демо-выдержка)",
)


@router.post("/ask", response_model=AskOut, response_model_by_alias=True)
async def ask(body: AskIn, response: Response, _: Employee = Depends(current_user)):
    response.headers["X-Stub"] = "true"
    q = body.question.lower()
    if "ночн" in q or "зарплат" in q and "начальник" in q:
        msg = "Надёжной информации об этом в базе знаний нет. Могу передать вопрос в HR."
        return AskOut(kind="no-answer", text=None, message=msg, sources=[], escalation="HR", answer=msg, answered=False, escalate_available=True, reason="no_match")
    text = "Ежегодный оплачиваемый отпуск — не менее 24 календарных дней [Ежегодный оплачиваемый отпуск, Продолжительность]."
    return AskOut(kind="grounded", text=text, message=None, sources=[SRC], escalation=None, answer=text, answered=True, escalate_available=False)


@router.get("/sources/{article_id}", response_model=KnowledgeArticle, response_model_by_alias=True)
async def source(article_id: str, response: Response, _: Employee = Depends(current_user)):
    response.headers["X-Stub"] = "true"
    return KnowledgeArticle(
        id=SRC.article_id, title=SRC.title, body="## Продолжительность\nНе менее 24 календарных дней…",
        updated_at=SRC.updated_at, country="KZ", source_label=SRC.source_label,
    )
