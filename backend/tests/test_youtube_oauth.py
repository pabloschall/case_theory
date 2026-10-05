from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.config.settings import Settings
from app.integrations.youtube.oauth import (
    YOUTUBE_READONLY_SCOPE,
    YOUTUBE_UPLOAD_SCOPE,
    authorization_url,
    authorized_channel,
    exchange_authorization_code,
    validate_oauth_state,
)


def youtube_settings() -> Settings:
    return Settings(
        _env_file=None,
        secret_key="test-secret-key-with-more-than-32-characters",
        youtube_client_id="client-id",
        youtube_client_secret="client-secret",
        youtube_redirect_uri="http://localhost:8000/api/v1/integrations/youtube/callback",
    )


def test_authorization_url_requests_offline_upload_and_channel_access() -> None:
    settings = youtube_settings()
    parsed = urlparse(authorization_url(settings))
    query = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.google.com"
    assert set(query["scope"][0].split()) == {YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE}
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["redirect_uri"] == [settings.youtube_redirect_uri]
    validate_oauth_state(query["state"][0], settings)


class FakeTokenResponse:
    is_error = False

    def json(self) -> dict[str, str]:
        return {"access_token": "access-token", "refresh_token": "refresh-token"}


class FakeChannelResponse:
    is_error = False

    def json(self) -> dict[str, object]:
        return {
            "items": [
                {
                    "id": "channel-id",
                    "snippet": {"title": "Case Researcher", "customUrl": "@CaseResearcher"},
                }
            ]
        }


class FakeAsyncClient:
    posted_data: dict[str, str] = {}

    def __init__(self, **_: Any) -> None:
        pass

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, _: str, *, data: dict[str, str]) -> FakeTokenResponse:
        FakeAsyncClient.posted_data = data
        return FakeTokenResponse()

    async def get(self, _: str, **__: Any) -> FakeChannelResponse:
        return FakeChannelResponse()


@pytest.mark.asyncio
async def test_code_exchange_returns_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    tokens = await exchange_authorization_code("authorization-code", youtube_settings())

    assert tokens.access_token == "access-token"
    assert tokens.refresh_token == "refresh-token"
    assert FakeAsyncClient.posted_data["grant_type"] == "authorization_code"
    assert FakeAsyncClient.posted_data["code"] == "authorization-code"


@pytest.mark.asyncio
async def test_authorized_channel_identifies_the_destination(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    channel = await authorized_channel("access-token")

    assert channel.id == "channel-id"
    assert channel.title == "Case Researcher"
    assert channel.handle == "@CaseResearcher"
