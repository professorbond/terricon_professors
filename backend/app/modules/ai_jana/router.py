from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.core.db import DbSession
from app.core.errors import not_found
from app.core.org.models import Employee
from app.core.profile import profile_registry
from app.modules.ai_jana import service
from app.modules.ai_jana.models import KbDoc
from app.modules.ai_jana.schemas import AskIn, AskOut, KnowledgeArticle

router = APIRouter(prefix="/api/ai", tags=["ai_jana"])


@router.post("/ask", response_model=AskOut, response_model_by_alias=True)
async def ask(body: AskIn, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    return (await service.ask(session, user, body.question, body.lang or user.lang)).out


@router.get("/sources/{article_id}", response_model=KnowledgeArticle, response_model_by_alias=True)
async def source(article_id: str, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    """Документ-источник. Только опубликованные документы страны пользователя; чужая страна → 404."""
    if article_id == service.OWN_DATA_ID:
        fields = await profile_registry.collect(session, user, user)
        bal = fields.get("leave_balance")
        body = "Данные 1С:ЗУП видны только вам.\n\n"
        if bal is not None:
            body += f"- Отпуск: {bal.days} дн. (на рассмотрении {bal.pending_days}, доступно {bal.available_days})\n"
        t = service.TEXTS.get(user.lang, service.TEXTS["ru"])
        from app.core import clock

        return KnowledgeArticle(id=article_id, title=t["own_data_title"], body=body, updated_at=clock.now(), country=user.country, source_label="1С:ЗУП")
    doc = await session.get(KbDoc, article_id)
    if doc is None or doc.status != "published" or doc.country != user.country:
        raise not_found("Документ не найден")
    return KnowledgeArticle(id=doc.id, title=doc.title, body=doc.body_md, updated_at=doc.updated_at, country=doc.country, source_label=doc.source_label)
