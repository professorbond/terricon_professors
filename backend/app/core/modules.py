"""Реестр модулей бэкенда. Каждый модуль — пакет в app/modules/ с переменной `module`:

    module = BackendModule(name="ext_wage", feature="wage_access", register=register)

    def register(ctx: ModuleContext) -> None:
        ctx.include_router(router)
        ctx.request_types.register(RequestType(...))
        ctx.events.subscribe("request.decided", on_decided)
        ctx.ticks.register("ext_wage", on_tick)
        ctx.profile.register(contribute_profile_fields)
        ctx.i18n(RU, KK)

Модуль с feature подключается, только если фича включена (EXT_FEATURES). Модели (models.py)
импортируются всегда — схема БД одна для всех, флаг выключает только поведение.
"""

import importlib
import pkgutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.events import EventBus
from app.core.i18n import register as register_i18n
from app.core.profile import ProfileRegistry
from app.core.requests.registry import RequestTypeRegistry
from app.core.ticks import TickRegistry


@dataclass
class ModuleContext:
    app: FastAPI
    settings: Settings
    events: EventBus
    request_types: RequestTypeRegistry
    ticks: TickRegistry
    profile: ProfileRegistry

    def include_router(self, router: APIRouter) -> None:
        self.app.include_router(router)

    def i18n(self, ru: dict[str, str], kk: dict[str, str] | None = None) -> None:
        register_i18n(ru, kk)


@dataclass(frozen=True)
class BackendModule:
    name: str
    register: Callable[[ModuleContext], None]
    feature: str | None = None  # None — модуль всегда включён
    # Тестовые данные модуля; вызывается после seed каркаса (app/seed/loader.py)
    seed: Callable[[AsyncSession], Awaitable[None]] | None = None
    description: str = field(default="")


def import_all_models() -> None:
    """Импортировать models.py всех модулей и интеграций (для Alembic и create_all)."""
    import app.core.notifications.models  # noqa: F401
    import app.core.org.models  # noqa: F401
    import app.core.requests.models  # noqa: F401
    import app.core.demo.models  # noqa: F401
    import app.integrations.bank.models  # noqa: F401
    import app.integrations.documentolog.models  # noqa: F401
    import app.integrations.zup.models  # noqa: F401
    import app.modules as modules_pkg

    for info in pkgutil.iter_modules(modules_pkg.__path__):
        try:
            importlib.import_module(f"app.modules.{info.name}.models")
        except ModuleNotFoundError as exc:
            if exc.name != f"app.modules.{info.name}.models":
                raise


def load_modules(names: list[str]) -> list[BackendModule]:
    return [importlib.import_module(f"app.modules.{name}").module for name in names]
