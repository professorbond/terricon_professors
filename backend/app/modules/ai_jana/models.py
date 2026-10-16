"""База знаний AI Jana и журнал вопросов (CLAUDE.md §7.7)."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class KbDoc(Base):
    __tablename__ = "kb_docs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # kb-kz-vacation
    country: Mapped[str] = mapped_column(ForeignKey("countries.code"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    source_label: Mapped[str] = mapped_column(String(300))
    body_md: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="published")  # published | draft
    updated_at: Mapped[datetime]


class KbQuestion(Base):
    """Вопросы к AI — БЕЗ идентификатора сотрудника (пробелы базы смотрит HR без имён)."""

    __tablename__ = "kb_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    question: Mapped[str] = mapped_column(Text)
    answered: Mapped[bool]
    top_score: Mapped[float]
    gap_group_id: Mapped[str | None] = mapped_column(String(36), default=None, index=True)
    asked_at: Mapped[datetime]
