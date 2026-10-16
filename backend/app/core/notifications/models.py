from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64))  # request.decided, course.assigned, ...
    title_key: Mapped[str] = mapped_column(String(128))
    body_key: Mapped[str] = mapped_column(String(128))
    params: Mapped[dict[str, Any]]
    # Совпадает с NotificationTarget фронтенда: {"kind": "request", "requestId": ...}
    target: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    link: Mapped[str | None] = mapped_column(String(256), default=None)
    read_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime]
