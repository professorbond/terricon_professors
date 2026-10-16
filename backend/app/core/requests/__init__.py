"""Движок заявок — общий для всех типов (отпуск, зарплата по факту, обращение, обмен сменой...).

Модуль типа: регистрирует RequestType в register(), принимает форму в своём эндпоинте,
валидирует payload и вызывает service.create(...). Всё остальное (статусы, история,
согласование, права, уведомления) делает движок. См. docs/EXTENSION_POINTS.md.
"""

from app.core.requests.registry import RequestType, request_types
from app.core.requests import service

__all__ = ["RequestType", "request_types", "service"]
