from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64))  # leave_order | wage_advance | ...
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    data: Mapped[dict[str, Any]]
    status: Mapped[str] = mapped_column(String(16))  # registered | cancelled
    external_number: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime]
