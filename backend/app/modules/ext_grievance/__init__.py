"""«Обращение» — механизм рассмотрения жалоб под стандарты ЕБРР (CLAUDE.md §7.6). Флаг: grievance.

Тип заявки grievance: согласующий — HR, срок — по политике (72 ч), отказ/решение — с причиной.
Анонимное обращение: автора не видит никто, кроме него самого; руководитель не видит обращений вообще.
В прототипе автор хранится в БД (чтобы он видел ответ) — честно указано в README."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.core.db import DbSession
from app.core.modules import BackendModule, ModuleContext
from app.core.org.models import Employee
from app.core.requests import RequestType
from app.core.requests import service as requests
from app.core.requests.models import Request
from app.core.requests.schemas import RequestOut, present
from app.core.schemas import ApiModel

TYPE = "grievance"
Category = Literal["safety", "pay", "manager", "conditions", "discrimination", "other"]

RU = {
    "request.type.grievance": "Обращение",
    "notif.grievance.resolved.title": "Ответ на обращение",
    "notif.grievance.resolved.body": "{number}: {comment}",
    "grievance.category.safety": "Безопасность",
    "grievance.category.pay": "Оплата труда",
    "grievance.category.manager": "Руководитель",
    "grievance.category.conditions": "Условия труда",
    "grievance.category.discrimination": "Дискриминация",
    "grievance.category.other": "Другое",
}
KK = {
    "request.type.grievance": "Өтініш-шағым",
    "notif.grievance.resolved.title": "Шағымға жауап",
    "notif.grievance.resolved.body": "{number}: {comment}",
    "grievance.category.safety": "Қауіпсіздік",
    "grievance.category.pay": "Еңбекақы",
    "grievance.category.manager": "Басшы",
    "grievance.category.conditions": "Еңбек жағдайы",
    "grievance.category.discrimination": "Кемсітушілік",
    "grievance.category.other": "Басқа",
}

router = APIRouter(prefix="/api/ext/grievances", tags=["ext: grievance"])


class GrievanceIn(ApiModel):
    category: Category
    text: str = Field(min_length=10, max_length=4000)
    anonymous: bool = False


@router.post("", response_model=RequestOut, response_model_by_alias=True, status_code=201)
async def submit(body: GrievanceIn, user: Employee = Depends(current_user), session: AsyncSession = DbSession):
    payload = {"category": body.category, "text": body.text.strip(), "anonymous": body.anonymous}
    return await present(session, await requests.create(session, user, TYPE, payload), user)


def is_anonymous(req: Request) -> bool:
    return req.type == TYPE and bool(req.payload.get("anonymous"))


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.request_types.register(
        RequestType(
            code=TYPE,
            number_prefix="GR",
            title_key="request.type.grievance",
            approver="hr",
            visible_to_manager=False,
            cancellable=True,
            comment_required_on_approve=True,
            hide_author=lambda req, _viewer: is_anonymous(req),
            decided_keys={
                "Approved": ("notif.grievance.resolved.title", "notif.grievance.resolved.body"),
                "Rejected": ("notif.grievance.resolved.title", "notif.grievance.resolved.body"),
            },
        )
    )
    ctx.include_router(router)


module = BackendModule(name="ext_grievance", feature="grievance", register=register, description="Обращения")
