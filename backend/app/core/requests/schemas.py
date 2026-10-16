from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.core.org.models import Employee
from app.core.requests import service
from app.core.requests.models import Request
from app.core.requests.registry import request_types
from app.core.schemas import ApiModel

SYSTEM_LABEL = {"ru": "Система", "kk": "Жүйе"}


class RequestEventOut(ApiModel):
    """Совпадает с LeaveRequestEvent фронтенда (+ event, data)."""

    id: str
    event: str
    status: str
    occurred_at: datetime
    actor_id: str | None
    actor_label: str
    comment: str | None
    data: dict[str, Any]


class DocumentRef(ApiModel):
    id: str
    kind: str
    number: str


class RequestPermissions(ApiModel):
    can_decide: bool
    can_cancel: bool


class RequestOut(ApiModel):
    id: str
    number: str
    type: str
    type_title: str
    status: str
    employee_id: str | None  # None — автор скрыт (анонимное обращение)
    employee_name: str | None
    approver_kind: str
    approver_id: str | None
    approver_name: str | None
    payload: dict[str, Any]
    submission_key: str | None
    created_at: datetime
    decided_at: datetime | None
    decided_by_system: bool
    decision_reason_code: str | None
    decision_comment: str | None
    version: int
    history: list[RequestEventOut]
    documents: list[DocumentRef]
    permissions: RequestPermissions


async def _names(session: AsyncSession, ids: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for emp_id in ids:
        emp = await session.get(Employee, emp_id)
        if emp is not None:
            out[emp_id] = emp.full_name
    return out


async def present(session: AsyncSession, req: Request, viewer: Employee) -> RequestOut:
    rtype = request_types.get(req.type)
    hidden = req.employee_id != viewer.id and rtype.hide_author(req, viewer)
    ids = {i for i in [req.employee_id, req.approver_id, *(e.actor_id for e in req.events)] if i}
    names = await _names(session, ids)
    lang = viewer.lang

    def actor_label(actor_id: str | None) -> str:
        if actor_id is None:
            return SYSTEM_LABEL.get(lang, SYSTEM_LABEL["ru"])
        if hidden and actor_id == req.employee_id:
            return t("request.anonymous_author", lang)
        return names.get(actor_id, "—")

    return RequestOut(
        id=req.id,
        number=req.number,
        type=req.type,
        type_title=t(rtype.title_key, lang),
        status=req.status,
        employee_id=None if hidden else req.employee_id,
        employee_name=None if hidden else names.get(req.employee_id),
        approver_kind=req.approver_kind,
        approver_id=req.approver_id,
        approver_name=names.get(req.approver_id) if req.approver_id else None,
        payload=req.payload,
        submission_key=req.submission_key if req.employee_id == viewer.id else None,
        created_at=req.created_at,
        decided_at=req.decided_at,
        decided_by_system=req.decided_by_system,
        decision_reason_code=req.decision_reason_code,
        decision_comment=req.decision_comment,
        version=req.version,
        history=[
            RequestEventOut(
                id=e.id,
                event=e.event,
                status=e.status,
                occurred_at=e.at,
                actor_id=None if hidden and e.actor_id == req.employee_id else e.actor_id,
                actor_label=actor_label(e.actor_id),
                comment=e.comment,
                data=e.data,
            )
            for e in req.events
        ],
        documents=[
            DocumentRef(id=e.data["documentId"], kind=e.data.get("documentKind", ""), number=e.data.get("documentNumber", ""))
            for e in req.events
            if "documentId" in e.data
        ],
        permissions=RequestPermissions(
            can_decide=service.can_decide(viewer, req), can_cancel=service.can_cancel(viewer, req)
        ),
    )
