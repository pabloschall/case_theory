from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.config.settings import Settings
from app.scheduled_reels import (
    YouTubeUploader,
    build_srt,
    build_youtube_description,
    case_hashtags,
    music_track_for_slot,
    reel_slot,
)


def test_reel_slot_changes_at_noon_utc() -> None:
    assert reel_slot(datetime(2026, 10, 5, 11, 59, tzinfo=UTC)) == "youtube:2026-10-05:am"
    assert reel_slot(datetime(2026, 10, 5, 12, 0, tzinfo=UTC)) == "youtube:2026-10-05:pm"


def test_build_srt_covers_the_complete_narration() -> None:
    subtitles = build_srt(["Opening fact", "Documented timeline", "Review the full case"], 45)
    assert "00:00:00,000 --> 00:00:15,000" in subtitles
    assert "00:00:30,000 --> 00:00:45,000" in subtitles
    assert "Review the full case" in subtitles


def test_music_tracks_alternate_between_schedule_slots() -> None:
    morning = music_track_for_slot("youtube:2026-10-05:am")
    evening = music_track_for_slot("youtube:2026-10-05:pm")
    next_morning = music_track_for_slot("youtube:2026-10-06:am")

    assert morning.name != evening.name
    assert morning == next_morning
    assert morning.is_file()
    assert evening.is_file()


def test_youtube_description_includes_sources_disclosure_site_and_hashtags() -> None:
    hashtags = case_hashtags(
        'Killing of Gabrielle ("Gabby") Petito — case summary',
        "Teton County, Wyoming",
    )
    description = build_youtube_description(
        "A concise description of this documented case.",
        ["https://source.example/one", "https://source.example/two"],
        "case-researcher.com",
        hashtags,
    )

    assert "https://case-researcher.com" in description
    assert "https://source.example/one" in description
    assert "AI-generated narration and background imagery" in description
    assert hashtags == ["#GabriellePetito", "#TetonCountyWyoming", "#CaseResearcher"]
    assert description.endswith("#GabriellePetito #TetonCountyWyoming #CaseResearcher")


def test_case_hashtags_omit_duplicate_location() -> None:
    assert case_hashtags("Phoenix case", "Phoenix") == ["#Phoenix", "#CaseResearcher"]


class FakeResponse:
    def __init__(self, data: dict[str, Any], *, headers: dict[str, str] | None = None) -> None:
        self.data = data
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.data


class FakeAsyncClient:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def __init__(self, **_: Any) -> None:
        pass

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        if "oauth2" in url:
            return FakeResponse({"access_token": "token"})
        return FakeResponse({}, headers={"Location": "https://upload.example/session"})

    async def put(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("PUT", url, kwargs))
        return FakeResponse({"id": "youtube-123"})


@pytest.mark.asyncio
async def test_youtube_uploader_refreshes_token_and_uses_resumable_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    settings = Settings(
        _env_file=None,
        youtube_client_id="client",
        youtube_client_secret="secret",
        youtube_refresh_token="refresh",
        youtube_privacy_status="public",
    )
    video_id = await YouTubeUploader(settings).upload(
        b"video-bytes",
        title="A sourced short",
        description="Documented case summary",
    )
    assert video_id == "youtube-123"
    assert [call[0] for call in FakeAsyncClient.calls] == ["POST", "POST", "PUT"]
    metadata = FakeAsyncClient.calls[1][2]["content"]
    assert '"privacyStatus": "public"' in metadata
    assert FakeAsyncClient.calls[2][1] == "https://upload.example/session"
