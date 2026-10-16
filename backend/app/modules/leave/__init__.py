"""Заявка «Отпуск» (тип vacation) на движке заявок (CLAUDE.md §5.2)."""

from app.core.modules import BackendModule
from app.modules.leave.register import register
from app.modules.leave.seed import seed

module = BackendModule(name="leave", register=register, seed=seed, description="Заявка на отпуск")
