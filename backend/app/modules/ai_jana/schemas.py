"""Ответ совместим и с AssistantAnswer фронтенда (kind/text/message/escalation),
и с форматом CLAUDE.md (answer/answered/escalateAvailable)."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.core.schemas import ApiModel


class AskIn(ApiModel):
    question: str = Field(min_length=1, max_length=1000)
    lang: Literal["ru", "kk"] | None = None


class KnowledgeSource(ApiModel):
    article_id: str
    title: str
    section: str
    updated_at: datetime
    source_label: str


class AskOut(ApiModel):
    kind: Literal["grounded", "no-answer"]
    text: str | None  # kind=grounded
    message: str | None  # kind=no-answer
    sources: list[KnowledgeSource]
    escalation: Literal["HR"] | None
    # Формат CLAUDE.md
    answer: str
    answered: bool
    escalate_available: bool
    # Почему нет ответа: no_match | other_person_data | no_sources
    reason: str | None = None


class KnowledgeArticle(ApiModel):
    id: str
    title: str
    body: str
    updated_at: datetime
    country: str
    source_label: str
