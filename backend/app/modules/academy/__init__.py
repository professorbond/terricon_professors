"""Jana Academy: каталог, назначенные курсы, уроки, тест, прогресс (CLAUDE.md §5.4)."""

from app.core.modules import BackendModule
from app.modules.academy.register import register
from app.modules.academy.seed import seed

module = BackendModule(name="academy", register=register, seed=seed, description="Jana Academy")
