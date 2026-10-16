from app.core.modules import ModuleContext
from app.modules.ai_jana.router import router


def register(ctx: ModuleContext) -> None:
    ctx.include_router(router)
