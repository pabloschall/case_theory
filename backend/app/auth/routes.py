from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import auth_rate_limit, verify_csrf
from app.auth.schemas import (
    AuthResponse,
    CsrfResponse,
    EmailRequest,
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenRequest,
)
from app.auth.security import new_csrf_token
from app.auth.service import AuthService
from app.common.errors import AppError
from app.config.settings import Settings, get_settings
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookies(response: Response, access: str, refresh: str, settings: Settings) -> None:
    response.set_cookie(
        settings.access_cookie_name,
        access,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )


def _clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.access_cookie_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(settings.refresh_cookie_name, path="/", domain=settings.cookie_domain)


@router.get("/csrf", response_model=CsrfResponse)
async def csrf(response: Response, settings: Settings = Depends(get_settings)) -> CsrfResponse:
    token = new_csrf_token()
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
        max_age=settings.refresh_token_days * 86400,
    )
    return CsrfResponse(csrf_token=token)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(auth_rate_limit)],
)
async def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    service = AuthService(db, settings)
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    user = await service.register(
        data,
        user_agent=user_agent,
        ip_address=ip_address,
        request_id=getattr(request.state, "request_id", None),
    )
    await service.request_email_verification(user.email)
    access, refresh = await service.create_session(
        user, user_agent, ip_address
    )
    _set_session_cookies(response, access, refresh, settings)
    return AuthResponse(message="Account created")


@router.post(
    "/email-verification/request",
    response_model=AuthResponse,
    dependencies=[Depends(verify_csrf), Depends(auth_rate_limit)],
)
async def request_email_verification(
    data: EmailRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    await AuthService(db, settings).request_email_verification(data.email)
    return AuthResponse(message="If the account needs verification, an email has been sent")


@router.post(
    "/email-verification/confirm",
    response_model=AuthResponse,
    dependencies=[Depends(verify_csrf), Depends(auth_rate_limit)],
)
async def confirm_email(
    data: TokenRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    await AuthService(db, settings).confirm_email(data.token)
    return AuthResponse(message="Email verified")


@router.post(
    "/password/forgot",
    response_model=AuthResponse,
    dependencies=[Depends(verify_csrf), Depends(auth_rate_limit)],
)
async def forgot_password(
    data: EmailRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    await AuthService(db, settings).request_password_reset(data.email)
    return AuthResponse(message="If an account exists for that email, a reset link has been sent")


@router.post(
    "/password/reset",
    response_model=AuthResponse,
    dependencies=[Depends(verify_csrf), Depends(auth_rate_limit)],
)
async def reset_password(
    data: PasswordResetRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    await AuthService(db, settings).reset_password(data.token, data.password)
    _clear_session_cookies(response, settings)
    return AuthResponse(message="Password reset successfully")


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(verify_csrf), Depends(auth_rate_limit)])
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    service = AuthService(db, settings)
    user = await service.authenticate(data.email, data.password)
    access, refresh = await service.create_session(
        user, request.headers.get("user-agent"), request.client.host if request.client else None
    )
    _set_session_cookies(response, access, refresh, settings)
    return AuthResponse(message="Signed in")


@router.post("/refresh", response_model=AuthResponse, dependencies=[Depends(verify_csrf)])
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise AppError(401, "invalid_session", "Session is invalid or expired")
    access, refresh_token = await AuthService(db, settings).rotate_session(token)
    _set_session_cookies(response, access, refresh_token, settings)
    return AuthResponse(message="Session refreshed")


@router.post("/logout", response_model=AuthResponse, dependencies=[Depends(verify_csrf)])
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    await AuthService(db, settings).revoke_session(request.cookies.get(settings.refresh_cookie_name))
    _clear_session_cookies(response, settings)
    return AuthResponse(message="Signed out")
