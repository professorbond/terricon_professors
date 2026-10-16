from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    amount: Mapped[int]
    reference: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))  # paid | failed
    created_at: Mapped[datetime]
