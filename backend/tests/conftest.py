"""Тесты на SQLite в памяти: схема через metadata.create_all, seed — как в проде."""

import os

os.environ.update(
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    AUTO_MIGRATE="false",
    AUTO_SEED="false",
    TICK_INTERVAL_SECONDS="0",
    DEMO_MODE="true",
    JWT_SECRET="test-secret-test-secret-test-secret-0000",
)

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import clock, db  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import Base  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
async def app():
    from datetime import timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.main import create_app
    from app.seed.loader import run_seed

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    db._engine = engine
    db._sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    clock.set_offset(timedelta(0))
    application = create_app()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with db.sessionmaker()() as session:
        await run_seed(session, application.state.modules)
        await session.commit()
    yield application
    clock.set_offset(timedelta(0))
    await engine.dispose()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def login(client):
    async def _login(name: str) -> dict[str, str]:
        r = await client.post("/api/auth/login", json={"login": name, "password": "demo1234"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['accessToken']}"}

    return _login
