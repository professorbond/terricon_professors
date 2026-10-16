"""Сборка приложения: каркас (core) + модули из app/modules/__init__.py::MODULES."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import i18n
from app.core.auth_router import router as auth_router
from app.core.config import Settings, get_settings
from app.core.db import sessionmaker
from app.core.demo.router import router as demo_router
from app.core.demo.service import load_offset
from app.core.errors import install_error_handlers
from app.core.events import events
from app.core.modules import ModuleContext, import_all_models, load_modules
from app.core.notifications.router import router as notifications_router
from app.core.profile import profile_registry
from app.core.requests import notifications as request_notifications
from app.core.requests.registry import request_types
from app.core.requests.router import router as requests_router
from app.core.settings_api import router as settings_router
from app.core.ticks import tick_loop, ticks
from app.modules import MODULES

log = logging.getLogger("janamen")


def run_migrations() -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")


async def startup(app: FastAPI) -> None:
    settings: Settings = app.state.settings
    if settings.auto_migrate:
        await asyncio.to_thread(run_migrations)
    from app.seed.loader import is_seeded, run_seed

    async with sessionmaker()() as session:
        await load_offset(session)
        if settings.auto_seed and not await is_seeded(session):
            log.info("Пустая база — применяю seed")
            await run_seed(session, app.state.modules)
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup(app)
    task = None
    if app.state.settings.tick_interval_seconds > 0:
        task = asyncio.create_task(tick_loop(app.state.settings.tick_interval_seconds))
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # Реестры глобальные — очищаем, чтобы повторная сборка (тесты) не задваивала подписки
    events.clear()
    request_types.clear()
    ticks.clear()
    profile_registry.clear()
    i18n.clear()
    import_all_models()

    app = FastAPI(title="JanaМен API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    for router in (auth_router, requests_router, notifications_router, settings_router):
        app.include_router(router)
    if settings.demo_mode:
        app.include_router(demo_router)
    request_notifications.register(events)

    ctx = ModuleContext(
        app=app, settings=settings, events=events, request_types=request_types, ticks=ticks, profile=profile_registry
    )
    enabled = []
    for module in load_modules(MODULES):
        if settings.feature_enabled(module.feature):
            module.register(ctx)
            enabled.append(module)
    app.state.modules = enabled
    app.state.enabled_features = {m.feature for m in enabled if m.feature}
    return app


app = create_app()
