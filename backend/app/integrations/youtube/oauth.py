import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

import httpx
import jwt

from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.config.settings import Settings

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_SCOPES = (YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE)
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class AuthorizedChannel:
    id: str
    title: str
    handle: str | None


def create_oauth_state(settings: Settings) -> str:
    now = utc_now()
    return jwt.encode(
        {
            "type": "youtube_oauth",
            "nonce": secrets.token_urlsafe(24),
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        settings.secret_key,
        algorithm="HS256",
    )


def validate_oauth_state(state: str, settings: Settings) -> None:
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise AppError(400, "invalid_youtube_oauth_state", "YouTube authorization has expired") from exc
    if payload.get("type") != "youtube_oauth" or not payload.get("nonce"):
        raise AppError(400, "invalid_youtube_oauth_state", "YouTube authorization state is invalid")


def authorization_url(settings: Settings) -> str:
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        raise AppError(
            503,
            "youtube_oauth_not_configured",
            "YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be configured",
        )
    query = urlencode(
        {
            "client_id": settings.youtube_client_id,
            "redirect_uri": settings.youtube_redirect_uri,
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": create_oauth_state(settings),
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_authorization_code(code: str, settings: Settings) -> OAuthTokens:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.youtube_redirect_uri,
            },
        )
    if response.is_error:
        raise AppError(
            400,
            "youtube_oauth_exchange_failed",
            "Google rejected the YouTube authorization code",
        )
    payload = response.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not isinstance(access_token, str) or not access_token:
        raise AppError(400, "youtube_access_token_missing", "Google did not return an access token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise AppError(
            400,
            "youtube_refresh_token_missing",
            "Google did not return a refresh token. Revoke the existing app grant and authorize again.",
        )
    return OAuthTokens(access_token=access_token, refresh_token=refresh_token)


async def authorized_channel(access_token: str) -> AuthorizedChannel:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            YOUTUBE_CHANNELS_URL,
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.is_error:
        raise AppError(
            400,
            "youtube_channel_lookup_failed",
            "The authorized YouTube channel could not be verified",
        )
    payload = response.json()
    items = payload.get("items")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise AppError(
            400,
            "youtube_channel_missing",
            "The authorized Google identity does not have a YouTube channel",
        )
    channel = items[0]
    snippet = channel.get("snippet")
    channel_id = channel.get("id")
    if not isinstance(channel_id, str) or not isinstance(snippet, dict):
        raise AppError(400, "youtube_channel_invalid", "Google returned invalid channel information")
    title = snippet.get("title")
    handle = snippet.get("customUrl")
    return AuthorizedChannel(
        id=channel_id,
        title=title if isinstance(title, str) else "Unknown channel",
        handle=handle if isinstance(handle, str) else None,
    )
