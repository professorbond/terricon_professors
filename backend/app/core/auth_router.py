from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user, issue_token, verify_password
from app.core.db import DbSession
from app.core.errors import AppError
from app.core.org.models import Employee
from app.core.org.service import find_by_login
from app.core.schemas import ApiModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(ApiModel):
    login: str
    password: str


class UserOut(ApiModel):
    """Совпадает с User фронтенда (+ country, lang)."""

    id: str
    display_name: str
    role: str
    country: str
    lang: str


class LoginOut(ApiModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def user_out(emp: Employee) -> UserOut:
    return UserOut(id=emp.id, display_name=emp.full_name, role=emp.role, country=emp.country, lang=emp.lang)


@router.post("/login", response_model=LoginOut, response_model_by_alias=True)
async def login(body: LoginIn, session: AsyncSession = DbSession) -> LoginOut:
    emp = await find_by_login(session, body.login.strip().lower())
    if emp is None or not emp.active or not verify_password(body.password, emp.password_hash):
        raise AppError("unauthenticated", "INVALID_CREDENTIALS", "Неверный логин или пароль")
    return LoginOut(access_token=issue_token(emp), user=user_out(emp))


@router.get("/me", response_model=UserOut, response_model_by_alias=True)
async def me(user: Employee = Depends(current_user)) -> UserOut:
    return user_out(user)


class LangIn(ApiModel):
    lang: str


@router.put("/me/lang", response_model=UserOut, response_model_by_alias=True)
async def set_lang(body: LangIn, user: Employee = Depends(current_user)) -> UserOut:
    """Язык интерфейса и уведомлений (ru/kk). Это настройка приложения, не кадровые данные."""
    if body.lang not in ("ru", "kk"):
        raise AppError("validation", "UNKNOWN_LANG", "Поддерживаются ru и kk", {"lang": ["ru | kk"]})
    user.lang = body.lang
    return user_out(user)
