from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest

from app.config.settings import Settings
from app.scheduled_reels import (
    SceneVisual,
    VertexVeoGenerator,
    YouTubeUploader,
    build_scene_metadata,
    build_srt,
    build_youtube_description,
    case_hashtags,
    fit_narration_duration,
    generate_scene_visuals,
    music_track_for_slot,
    reel_slot,
)


def test_reel_slot_changes_at_noon_utc() -> None:
    assert reel_slot(datetime(2026, 10, 5, 11, 59, tzinfo=UTC)) == "youtube:2026-10-05:am"
    assert reel_slot(datetime(2026, 10, 5, 12, 0, tzinfo=UTC)) == "youtube:2026-10-05:pm"


def test_build_srt_covers_the_complete_narration() -> None:
    subtitles = build_srt(
        ["Opening fact", "Documented timeline", "Review the full case"],
        [8.5, 21.5, 15],
    )
    assert "00:00:00,000 --> 00:00:08,500" in subtitles
    assert "00:00:30,000 --> 00:00:45,000" in subtitles
    assert "Review the full case" in subtitles


def test_scene_metadata_preserves_prompts_and_narration_timing() -> None:
    scenes = build_scene_metadata(
        ["The location", "The timeline"],
        ["A specific desert road at dusk", "A period calendar beside a case file"],
        ["The case began near a desert road.", "Investigators documented the timeline."],
        [8.5, 12.25],
    )

    assert scenes[0]["visual_direction"] == "A specific desert road at dusk"
    assert scenes[1]["narration_text"] == "Investigators documented the timeline."
    assert scenes[1]["start_second"] == 8
    assert scenes[1]["end_second"] == 21


@pytest.mark.asyncio
async def test_overlong_narration_is_fitted_to_short_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "narration.mp3"
    audio_path.write_bytes(b"audio")
    commands: list[tuple[str, ...]] = []

    async def fake_run_process(*command: str) -> bytes:
        commands.append(command)
        return b""

    async def fake_audio_duration(_: Any) -> float:
        return 55.2

    monkeypatch.setattr("app.scheduled_reels._run_process", fake_run_process)
    monkeypatch.setattr("app.scheduled_reels.audio_duration", fake_audio_duration)

    fitted_path, durations = await fit_narration_duration(audio_path, [20.0, 21.0, 19.0])

    assert fitted_path.name == "narration-fitted.mp3"
    assert sum(durations) == pytest.approx(55.2)
    assert commands[0][commands[0].index("-filter:a") + 1] == "atempo=1.09090909"


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
    assert "AI-generated narration and background visuals" in description
    assert hashtags == ["#GabriellePetito", "#TetonCountyWyoming", "#CaseResearcher"]
    assert description.endswith("#GabriellePetito #TetonCountyWyoming #CaseResearcher")


def test_case_hashtags_omit_duplicate_location() -> None:
    assert case_hashtags("Phoenix case", "Phoenix") == ["#Phoenix", "#CaseResearcher"]


def test_vertex_veo_generator_requests_a_silent_portrait_clip() -> None:
    calls: list[dict[str, Any]] = []

    class FakeModels:
        def generate_videos(self, **kwargs: Any) -> SimpleNamespace:
            calls.append(kwargs)
            video = SimpleNamespace(video_bytes=b"veo-video")
            result = SimpleNamespace(generated_videos=[SimpleNamespace(video=video)])
            return SimpleNamespace(done=True, result=result)

    class FakeTypes:
        GenerateVideosSource = staticmethod(lambda **kwargs: kwargs)
        GenerateVideosConfig = staticmethod(lambda **kwargs: kwargs)

    generator = object.__new__(VertexVeoGenerator)
    generator.settings = Settings(_env_file=None, reel_video_project_id="case-theory")
    generator.types = FakeTypes
    generator.client = SimpleNamespace(models=FakeModels())

    assert generator._generate("A documented desert road at dusk") == b"veo-video"
    assert calls[0]["source"] == {"prompt": "A documented desert road at dusk"}
    assert calls[0]["config"]["aspect_ratio"] == "9:16"
    assert calls[0]["config"]["duration_seconds"] == 8
    assert calls[0]["config"]["generate_audio"] is False


@pytest.mark.asyncio
async def test_scene_visuals_use_vertex_veo(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeVeoGenerator:
        def __init__(self, _: Settings) -> None:
            pass

        async def generate(self, prompt: str) -> bytes:
            return f"video:{prompt}".encode()

    monkeypatch.setattr("app.scheduled_reels.VertexVeoGenerator", FakeVeoGenerator)
    settings = Settings(_env_file=None, reel_visual_provider="vertex_veo")
    visuals = await generate_scene_visuals(
        cast(Any, object()),
        settings,
        ["scene one", "scene two"],
    )

    assert visuals == [
        SceneVisual(b"video:scene one", "video"),
        SceneVisual(b"video:scene two", "video"),
    ]


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
