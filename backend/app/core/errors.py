"""Единый формат ошибок API, совместимый с ServiceProblem фронтенда:

    {"kind": "forbidden", "code": "FORBIDDEN", "message": "...", "fieldErrors": {...}, "data": {...}}
"""

from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

ProblemKind = Literal["unauthenticated", "forbidden", "not-found", "validation", "conflict", "unavailable"]

STATUS_BY_KIND: dict[str, int] = {
    "unauthenticated": 401,
    "forbidden": 403,
    "not-found": 404,
    "validation": 422,
    "conflict": 409,
    "unavailable": 503,
}


class AppError(Exception):
    def __init__(
        self,
        kind: ProblemKind,
        code: str,
        message: str,
        field_errors: dict[str, list[str]] | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.message = message
        self.field_errors = field_errors
        self.data = data

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "kind": self.kind,
            "code": self.code,
            "message": self.message,
            "messageKey": f"errors.{self.code}",  # для перевода на фронтенде (ru/kk)
        }
        if self.field_errors:
            body["fieldErrors"] = self.field_errors
        if self.data:
            body["data"] = self.data
        return body


def forbidden(message: str = "Недостаточно прав") -> AppError:
    return AppError("forbidden", "FORBIDDEN", message)


def not_found(message: str = "Не найдено") -> AppError:
    return AppError("not-found", "NOT_FOUND", message)


def validation(code: str, message: str, field: str | None = None, data: dict[str, Any] | None = None) -> AppError:
    return AppError("validation", code, message, {field: [message]} if field else None, data)


def conflict(code: str, message: str, data: dict[str, Any] | None = None) -> AppError:
    return AppError("conflict", code, message, data=data)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(exc.to_body(), status_code=STATUS_BY_KIND[exc.kind])

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields.setdefault(".".join(loc) or "_", []).append(err.get("msg", "invalid"))
        body = AppError("validation", "VALIDATION", "Проверьте введённые данные", fields).to_body()
        return JSONResponse(body, status_code=422)

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        # Нарушение уникальности/ссылок из-за параллельных запросов — конфликт, а не 500
        body = AppError("conflict", "CONFLICT", "Данные изменились параллельно, повторите действие").to_body()
        return JSONResponse(body, status_code=409)

    @app.exception_handler(DBAPIError)
    async def _db_error(_: Request, exc: DBAPIError) -> JSONResponse:
        if "deadlock" in str(exc.orig).lower() or "could not serialize" in str(exc.orig).lower():
            body = AppError("conflict", "CONFLICT", "Параллельное изменение, повторите действие").to_body()
            return JSONResponse(body, status_code=409)
        raise exc

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        kind = {401: "unauthenticated", 403: "forbidden", 404: "not-found", 409: "conflict"}.get(exc.status_code, "validation")
        code = f"HTTP_{exc.status_code}"
        body = {"kind": kind, "code": code, "message": str(exc.detail), "messageKey": f"errors.{code}"}
        return JSONResponse(body, status_code=exc.status_code)
