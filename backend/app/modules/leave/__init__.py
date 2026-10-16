"""Заявка «Отпуск» — эталонный модуль на движке заявок (образец для остальных типов)."""

from app.core.modules import BackendModule
from app.modules.leave.register import register
from app.modules.leave.seed import seed

module = BackendModule(name="leave", register=register, seed=seed, description="Заявка на отпуск")
