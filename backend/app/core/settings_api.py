from fastapi import APIRouter, Depends, Request

from app.core.auth import current_user
from app.core.config import get_settings
from app.core.org.models import Employee
from app.core.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsOut(ApiModel):
    features: list[str]
    demo_mode: bool
    country: str
    lang: str
    llm_available: bool


@router.get("/settings", response_model=SettingsOut, response_model_by_alias=True)
async def app_settings(request: Request, user: Employee = Depends(current_user)) -> SettingsOut:
    s = get_settings()
    return SettingsOut(
        features=sorted(request.app.state.enabled_features),
        demo_mode=s.demo_mode,
        country=user.country,
        lang=user.lang,
        llm_available=bool(s.anthropic_api_key),
    )


@router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
