"""AI Jana: ответы только по базе знаний страны пользователя, с источником (CLAUDE.md §7.7)."""

from app.core.modules import BackendModule
from app.modules.ai_jana.register import register
from app.modules.ai_jana.seed import seed

module = BackendModule(name="ai_jana", register=register, seed=seed, description="AI Jana")
