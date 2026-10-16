"""Профиль сотрудника, команда, карточки сотрудников (CLAUDE.md §5.1). Данные — только чтение."""

from app.core.modules import BackendModule
from app.modules.profile.router import router


def register(ctx) -> None:  # noqa: ANN001
    ctx.include_router(router)


module = BackendModule(name="profile", register=register, description="Профиль и команда")
