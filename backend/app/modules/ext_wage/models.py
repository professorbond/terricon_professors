from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Withdrawal(Base):
    """Выводы «Зарплаты по факту». Радар удержания эту таблицу НЕ читает (CLAUDE.md §7.5)."""

    __tablename__ = "ext_wage_withdrawals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    period: Mapped[str] = mapped_column(String(7))  # 2026-10
    amount: Mapped[int]
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), default=None)
    payout_id: Mapped[str | None] = mapped_column(ForeignKey("payouts.id"), default=None)
    status: Mapped[str] = mapped_column(String(16))  # pending | paid | failed
    created_at: Mapped[datetime]
