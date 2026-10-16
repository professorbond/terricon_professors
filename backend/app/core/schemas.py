"""Базовые схемы API: camelCase в JSON, snake_case в Python."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class Page(ApiModel, Generic[T]):
    """Совпадает с Page<T> фронтенда. Пагинации пока нет: nextCursor всегда null."""

    items: list[T]
    next_cursor: str | None = None
