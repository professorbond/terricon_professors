"""Гарантии и политики: ответ в срок, отказ только с причиной (CLAUDE.md §7.1). Флаг: guarantees."""

from app.core.modules import BackendModule
from app.modules.ext_guarantees.register import register
from app.modules.ext_guarantees.seed import seed

module = BackendModule(name="ext_guarantees", feature="guarantees", register=register, seed=seed, description="Гарантии")
