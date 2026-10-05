from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.auth.dependencies import require_admin
from app.common.errors import AppError
from app.config.settings import Settings, get_settings
from app.integrations.youtube.oauth import (
    authorization_url,
    authorized_channel,
    exchange_authorization_code,
    validate_oauth_state,
)

router = APIRouter(
    prefix="/integrations/youtube",
    tags=["youtube"],
    dependencies=[Depends(require_admin)],
)


@router.get("/connect", response_class=RedirectResponse)
async def connect_youtube(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    return RedirectResponse(authorization_url(settings), status_code=302)


@router.get("/callback", response_class=PlainTextResponse)
async def youtube_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if error:
        raise AppError(400, "youtube_oauth_denied", "YouTube authorization was denied")
    if not code or not state:
        raise AppError(400, "youtube_oauth_incomplete", "YouTube authorization response is incomplete")
    validate_oauth_state(state, settings)
    tokens = await exchange_authorization_code(code, settings)
    channel = await authorized_channel(tokens.access_token)
    channel_label = f"{channel.title} ({channel.handle})" if channel.handle else channel.title
    response = PlainTextResponse(
        "YouTube authorization complete.\n\n"
        f"Authorized channel: {channel_label}\n"
        f"Channel ID: {channel.id}\n\n"
        "Confirm this is @CaseResearcher, then copy these lines into your .env or production secret store:\n\n"
        f"YOUTUBE_REFRESH_TOKEN={tokens.refresh_token}\n"
        f"YOUTUBE_CHANNEL_ID={channel.id}\n"
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
