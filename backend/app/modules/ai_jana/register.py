from app.core.modules import ModuleContext
from app.modules.ai_jana.stub import router


def register(ctx: ModuleContext) -> None:
    ctx.include_router(router)
