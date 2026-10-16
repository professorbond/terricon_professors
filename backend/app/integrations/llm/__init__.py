"""LLM-шлюз. Без ANTHROPIC_API_KEY возвращает None — вызывающий код работает в экстрактивном
режиме (ответ фрагментом базы знаний). Ключ только из env, никогда во фронтенде.
Реальный вызов Anthropic подключит модуль AI Jana (Даниил)."""

from app.core.config import get_settings


def is_available() -> bool:
    return bool(get_settings().anthropic_api_key)


async def complete(system: str, messages: list[dict[str, str]], max_tokens: int = 800) -> str | None:
    if not is_available():
        return None
    # TODO(dan): вызов Anthropic Messages API (модуль ai_jana)
    return None
