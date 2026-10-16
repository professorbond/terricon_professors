from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class KbGapGroup(Base):
    """Группа похожих вопросов без ответа (CLAUDE.md §7.10). Без имён тех, кто спрашивал."""

    __tablename__ = "ext_kb_gap_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    label: Mapped[str] = mapped_column(String(300))
    question_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | drafted | published
    draft_doc_id: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime]
    last_asked_at: Mapped[datetime]
