import secrets
import uuid

import jwt
import structlog
from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.security import decode_token
from app.common.errors import AppError
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.users.models import User

log = structlog.get_logger()


async def verify_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if not cookie_token or not x_csrf_token or not secrets.compare_digest(cookie_token, x_csrf_token):
        raise AppError(403, "csrf_failed", "CSRF validation failed")


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User:
    access_token = request.cookies.get(settings.access_cookie_name)
    if not access_token:
        raise AppError(401, "authentication_required", "Authentication is required")
    try:
        payload = decode_token(access_token, "access", settings)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise AppError(401, "invalid_access_token", "Access session is invalid or expired") from exc
    user = await db.scalar(select(User).where(User.id == user_id).options(selectinload(User.profile)))
    if user is None or not user.is_active:
        raise AppError(401, "invalid_access_token", "Access session is invalid or expired")
    return user


async def get_optional_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not request.cookies.get(settings.access_cookie_name):
        return None
    return await get_current_user(request, settings, db)


async def require_admin(user: User = Depends(get_current_user)) -> None:
    if not user.is_admin:
        raise AppError(403, "admin_required", "Administrator access is required")


async def auth_rate_limit(request: Request, settings: Settings = Depends(get_settings)) -> None:
    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis is None:
        return
    client = request.client.host if request.client else "unknown"
    key = f"rate:auth:{client}:{request.url.path}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.auth_rate_window_seconds)
        if count > settings.auth_rate_limit:
            raise AppError(429, "rate_limited", "Too many authentication attempts. Try again shortly.")
    except AppError:
        raise
    except Exception:
        await log.awarning("auth_rate_limiter_unavailable")
