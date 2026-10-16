"""Серверные тексты (уведомления) на ru/kk. Модули регистрируют свои ключи в register()."""

from typing import Any

LANGS = ("ru", "kk")

_catalog: dict[str, dict[str, str]] = {"ru": {}, "kk": {}}


def register(ru: dict[str, str], kk: dict[str, str] | None = None) -> None:
    _catalog["ru"].update(ru)
    _catalog["kk"].update(kk or {})


def clear() -> None:
    for lang in LANGS:
        _catalog[lang].clear()


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def t(key: str, lang: str = "ru", params: dict[str, Any] | None = None) -> str:
    """Параметр с суффиксом _key сам переводится: {"type_key": "request.type.leave"} → {type}."""
    template = _catalog.get(lang, {}).get(key) or _catalog["ru"].get(key) or key
    values: dict[str, Any] = {}
    for name, value in (params or {}).items():
        if name.endswith("_key") and isinstance(value, str):
            values[name[:-4]] = t(value, lang)
        else:
            values[name] = "" if value is None else value
    return template.format_map(_SafeDict(values))
