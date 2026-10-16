"""JWT-авторизация. Пользователь всегда берётся из токена, а не из тела запроса."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import DbSession
from app.core.errors import AppError
from app.core.org.models import Employee

_bearer = HTTPBearer(auto_error=False)
_ITERATIONS = 100_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, _digest = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def issue_token(emp: Employee) -> str:
    s = get_settings()
    # exp — по реальному времени, а не clock.now(): перевод часов в демо не должен разлогинивать
    payload = {
        "sub": emp.id,
        "role": emp.role,
        "country": emp.country,
        "name": emp.full_name,
        "exp": datetime.now(UTC) + timedelta(hours=s.jwt_ttl_hours),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def _unauthenticated(message: str = "Требуется вход") -> AppError:
    return AppError("unauthenticated", "UNAUTHENTICATED", message)


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = DbSession,
) -> Employee:
    if creds is None:
        raise _unauthenticated()
    try:
        payload = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise _unauthenticated("Сессия истекла, войдите снова") from None
    emp = await session.get(Employee, payload.get("sub"))
    if emp is None or not emp.active:
        raise _unauthenticated()
    return emp

