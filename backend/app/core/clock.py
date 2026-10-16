"""Единственный источник текущего времени. Демо «переводит время» через смещение.

В бизнес-логике используйте только clock.now() / clock.today(), никогда datetime.now().
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

_offset = timedelta(0)

# Таймзона по умолчанию для календарных дат (сотрудники KZ/KG — UTC+5/UTC+6)
DEFAULT_TZ = ZoneInfo("Asia/Almaty")


def now() -> datetime:
    return datetime.now(UTC) + _offset


def today(tz: ZoneInfo = DEFAULT_TZ) -> date:
    return now().astimezone(tz).date()


def offset() -> timedelta:
    return _offset


def set_offset(value: timedelta) -> None:
    global _offset
    _offset = value
