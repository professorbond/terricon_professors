from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DemoState(Base):
    """Одна строка: смещение «демо-часов» относительно реального времени."""

    __tablename__ = "demo_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    offset_seconds: Mapped[int] = mapped_column(default=0)
