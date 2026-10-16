"""Jana Academy: каталог, назначенные курсы, уроки, тест, прогресс (CLAUDE.md §5.4)."""

from app.core.modules import BackendModule
from app.modules.academy.register import register

module = BackendModule(name="academy", register=register, description="Jana Academy")
