import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.common.timestamps import utc_now
from app.config.settings import Settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    now = utc_now()
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        },
        settings.secret_key,
        algorithm="HS256",
    )


def create_refresh_token(user_id: uuid.UUID, session_id: uuid.UUID, settings: Settings) -> tuple[str, Any]:
    now = utc_now()
    expires_at = now + timedelta(days=settings.refresh_token_days)
    token = jwt.encode(
        {"sub": str(user_id), "sid": str(session_id), "type": "refresh", "iat": now, "exp": expires_at},
        settings.secret_key,
        algorithm="HS256",
    )
    return token, expires_at


def decode_token(token: str, expected_type: str, settings: Settings) -> dict[str, Any]:
    payload: dict[str, Any] = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def new_account_token() -> str:
    return secrets.token_urlsafe(48)
