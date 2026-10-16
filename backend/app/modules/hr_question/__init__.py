"""«Вопрос к HR» — эскалация из AI Jana (CLAUDE.md §5.6). Простой тип заявки, согласующий — HR."""

from app.core.modules import BackendModule
from app.modules.hr_question.register import register
from app.modules.hr_question.seed import seed

module = BackendModule(name="hr_question", register=register, seed=seed, description="Вопрос к HR")
