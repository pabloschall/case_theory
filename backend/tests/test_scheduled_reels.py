import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest

from app.config.settings import Settings
from app.scheduled_reels import (
    SceneVisual,
    VeoSafetyFilteredError,
    VertexVeoGenerator,
    YouTubeUploader,
    build_scene_metadata,
    build_srt,
    build_veo_safety_retry_prompt,
    build_youtube_description,
    case_hashtags,
    fit_narration_duration,
    generate_scene_visuals,
    manual_reel_slot,
    music_track_for_slot,
    reel_slot,
    render_vertical_video,
)


def test_reel_slot_changes_at_noon_utc() -> None:
    assert reel_slot(datetime(2026, 10, 5, 11, 59, tzinfo=UTC)) == "youtube:2026-10-05:am"
    assert reel_slot(datetime(2026, 10, 5, 12, 0, tzinfo=UTC)) == "youtube:2026-10-05:pm"


def test_manual_reel_slot_is_unique_from_scheduled_slots() -> None:
    slot = manual_reel_slot(datetime(2026, 10, 6, 17, 32, 17, 118258, tzinfo=UTC))

    assert slot == "youtube:manual:2026-10-06T17:32:17.118258Z"


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


def test_music_track_supports_manual_slots() -> None:
    slot = "youtube:manual:2026-10-06T17:32:17.118258Z"

    assert music_track_for_slot(slot) == music_track_for_slot(slot)
    assert music_track_for_slot(slot).is_file()


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
    assert calls[0]["config"]["person_generation"] == "allow_adult"


def test_reel_video_duration_parses_cloud_run_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REEL_VIDEO_DURATION_SECONDS", "8")

    settings = Settings(_env_file=None)

    assert settings.reel_video_duration_seconds == 8


@pytest.mark.asyncio
async def test_render_appends_advertising_clip_and_collaboration_card(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []
    music_path = tmp_path / "music.mp3"
    advertising_path = tmp_path / "advertising.mp4"
    music_path.write_bytes(b"music")
    advertising_path.write_bytes(b"advertising")

    async def fake_run_process(*command: str) -> bytes:
        commands.append(command)
        if command[-1].endswith("reel.mp4"):
            await asyncio.to_thread(Path(command[-1]).write_bytes, b"rendered-video")
        return b""

    async def fake_audio_duration(_: Path) -> float:
        return 10.0

    async def fake_media_duration(path: Path) -> float:
        assert path == advertising_path
        return 6.0

    monkeypatch.setattr("app.scheduled_reels._run_process", fake_run_process)
    monkeypatch.setattr("app.scheduled_reels.audio_duration", fake_audio_duration)
    monkeypatch.setattr("app.scheduled_reels.media_duration", fake_media_duration)

    video, duration, scenes = await render_vertical_video(
        tmp_path,
        [SceneVisual(b"image", "image")],
        [b"narration"],
        ["The documented case"],
        ["A specific case location"],
        ["The documented narration."],
        "case-researcher.com",
        music_path,
        0.1,
        advertising_path,
    )

    final_command = commands[-1]
    filter_graph = final_command[final_command.index("-filter_complex") + 1]
    assert video == b"rendered-video"
    assert duration == 20
    assert str(advertising_path) in final_command
    assert "[vadvertising][vend]concat=n=3" in filter_graph
    assert "Explore the full case" in filter_graph
    assert "and collaborate with others" in filter_graph
    assert "www.case-researcher.com" in filter_graph
    assert scenes[-2]["start_second"] == 10
    assert scenes[-2]["end_second"] == 16
    assert scenes[-1]["end_second"] == duration


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


def test_veo_safety_retry_prompt_requires_an_empty_symbolic_scene() -> None:
    prompt = build_veo_safety_retry_prompt("A witness enters a house at dusk")

    assert "only an empty environment and neutral inanimate objects" in prompt
    assert "Do not show people, faces" in prompt
    assert "A witness enters a house at dusk" in prompt


@pytest.mark.asyncio
async def test_scene_visuals_retry_safety_filtered_veo_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []

    class FakeVeoGenerator:
        def __init__(self, _: Settings) -> None:
            pass

        async def generate(self, prompt: str) -> bytes:
            prompts.append(prompt)
            if len(prompts) == 1:
                raise VeoSafetyFilteredError("people/face generation filtered")
            return b"safe-video"

    monkeypatch.setattr("app.scheduled_reels.VertexVeoGenerator", FakeVeoGenerator)
    settings = Settings(_env_file=None, reel_visual_provider="vertex_veo")

    visuals = await generate_scene_visuals(cast(Any, object()), settings, ["A person at a doorway"])

    assert visuals == [SceneVisual(b"safe-video", "video")]
    assert prompts[0] == "A person at a doorway"
    assert "Do not show people, faces" in prompts[1]


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


@pytest.mark.asyncio
async def test_youtube_uploader_explains_an_expired_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ExpiredTokenClient:
        def __init__(self, **_: Any) -> None:
            pass

        async def __aenter__(self) -> "ExpiredTokenClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, url: str, **_: Any) -> httpx.Response:
            request = httpx.Request("POST", url)
            return httpx.Response(
                400,
                request=request,
                json={
                    "error": "invalid_grant",
                    "error_description": "Token has been expired or revoked.",
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", ExpiredTokenClient)
    settings = Settings(
        _env_file=None,
        youtube_client_id="client",
        youtube_client_secret="secret",
        youtube_refresh_token="expired-refresh-token",
    )

    with pytest.raises(RuntimeError, match="invalid_grant.*expired or revoked.*In production"):
        await YouTubeUploader(settings).upload(
            b"video-bytes",
            title="A sourced short",
            description="Documented case summary",
        )
