"""Настройки приложения из переменных окружения (см. .env.example в корне репозитория)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://janamen:janamen@localhost:5432/janamen"
    jwt_secret: str = "dev-only-change-me-dev-only-change-me"
    jwt_ttl_hours: int = 12
    demo_mode: bool = True
    # Применять миграции и seed при старте, если база пустая
    auto_migrate: bool = True
    auto_seed: bool = True
    # Фоновый тик (гарантии, сигналы). 0 — выключен (тесты)
    tick_interval_seconds: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    # Включённые ext-фичи Даниила через запятую, "*" — все
    ext_features: str = "*"
    # Гарантии: отказ только с кодом причины из справочника (CLAUDE.md §7.1).
    # false — временно, пока во фронтенде нет выбора причины: без кода ставится OTHER
    guarantees_require_reason: bool = True
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def feature_enabled(self, feature: str | None) -> bool:
        if feature is None:
            return True
        enabled = {f.strip() for f in self.ext_features.split(",") if f.strip()}
        return "*" in enabled or feature in enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
