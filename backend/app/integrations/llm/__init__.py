"""LLM-шлюз (Anthropic Claude). Без ANTHROPIC_API_KEY или при ошибке API возвращает None —
вызывающий код работает в экстрактивном режиме (ответ фрагментом базы знаний).
Ключ только из env, никогда во фронтенде."""

import logging

import anthropic

from app.core.config import get_settings

log = logging.getLogger("janamen.llm")

_client: anthropic.AsyncAnthropic | None = None


def is_available() -> bool:
    return bool(get_settings().anthropic_api_key)


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        # Короткий таймаут: пользователь ждёт ответа в чате; при сбое — экстрактивный режим
        _client = anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key, timeout=25.0, max_retries=1)
    return _client


async def complete(system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> str | None:
    """Текст ответа модели или None (нет ключа, отказ модели, ошибка сети/API)."""
    if not is_available():
        return None
    try:
        response = await _get_client().beta.messages.create(
            model=get_settings().anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,  # type: ignore[arg-type]
            # Короткие ответы по готовым фрагментам — низкое усилие, быстрее
            output_config={"effort": "low"},
            # При отказе классификатора запрос переисполнится на рекомендованной модели
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.RateLimitError:
        log.warning("LLM rate limited — экстрактивный режим")
        return None
    except anthropic.APIStatusError as exc:
        log.warning("LLM API error %s — экстрактивный режим", exc.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("LLM недоступен (сеть/таймаут) — экстрактивный режим")
        return None
    if response.stop_reason == "refusal":
        return None
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None
