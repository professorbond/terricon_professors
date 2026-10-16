from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from app.core.errors import AppError
from app.core.org.models import Employee
from app.core.requests.models import Request

ApproverKind = Literal["manager", "hr", "none"]


@dataclass(frozen=True)
class RequestType:
    code: str  # "leave", "wage_access", "grievance", ...
    number_prefix: str  # видимый номер: JL-2026-0001
    title_key: str  # ключ i18n названия типа
    approver: ApproverKind = "manager"
    cancellable: bool = True
    # Руководитель видит заявки своей команды этого типа (обращения — нет)
    visible_to_manager: bool = True
    # Скрыть автора от этого зрителя (анонимные обращения). Автор себя видит всегда.
    hide_author: Callable[[Request, Employee], bool] = field(default=lambda _req, _viewer: False)


class RequestTypeRegistry:
    def __init__(self) -> None:
        self._types: dict[str, RequestType] = {}

    def register(self, rtype: RequestType) -> None:
        if rtype.code in self._types:
            raise ValueError(f"Тип заявки {rtype.code} уже зарегистрирован")
        self._types[rtype.code] = rtype

    def get(self, code: str) -> RequestType:
        try:
            return self._types[code]
        except KeyError:
            raise AppError("validation", "UNKNOWN_REQUEST_TYPE", f"Неизвестный тип заявки: {code}") from None

    def all(self) -> list[RequestType]:
        return list(self._types.values())

    def clear(self) -> None:
        self._types.clear()


request_types = RequestTypeRegistry()
