from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token") from exc


def create_token_for_user(user: dict[str, Any], extra_claims: dict[str, Any] | None = None, expires_delta: timedelta | None = None) -> str:
    user_id = str(user.get("_id") or user.get("id"))
    payload = {
            "sub": user_id,
            "email": user["email"],
            "role": user["role"],
        }
    if extra_claims:
        payload.update(extra_claims)
    return create_access_token(payload, expires_delta=expires_delta)
