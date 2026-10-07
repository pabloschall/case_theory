"""Create and publish one sourced YouTube Short for the current twelve-hour slot."""

import argparse
import asyncio
import base64
import hashlib
import json
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import httpx
import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cases.models import Case, CaseSummary, Source
from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.config.settings import Settings, get_settings
from app.db import models as _models  # noqa: F401  Register every mapper for the standalone job.
from app.integrations.youtube.oauth import authorized_channel
from app.reels.models import ReelDraft
from app.storage.provider import get_storage_provider

logger = structlog.get_logger()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MAX_NARRATION_SECONDS = 56.0
TARGET_NARRATION_SECONDS = 55.0
MUSIC_TRACKS = (
    Path(__file__).resolve().parent / "reels" / "assets" / "landing-1.mp3",
    Path(__file__).resolve().parent / "reels" / "assets" / "landing_2.mp3",
)
HASHTAG_STOP_WORDS = {"a", "an", "and", "case", "criminal", "killing", "of", "summary", "the"}
VEO_NEGATIVE_PROMPT = (
    "readable text, captions, logos, watermarks, graphic violence, blood, weapons in use, identifiable real people, "
    "distorted faces, extra limbs, surveillance overlays, generic police lights"
)


@dataclass(frozen=True)
class SceneVisual:
    content: bytes
    kind: Literal["image", "video"]


class GeneratedReelScene(BaseModel):
    narration_text: str = Field(min_length=20, max_length=500)
    on_screen_text: str = Field(min_length=2, max_length=90)
    image_prompt: str = Field(min_length=20, max_length=1000)


class GeneratedReelScript(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    hook: str = Field(min_length=3, max_length=180)
    narration: str = Field(min_length=300, max_length=1000)
    caption: str = Field(min_length=20, max_length=1800)
    scenes: list[GeneratedReelScene] = Field(min_length=3, max_length=6)

    @field_validator("narration")
    @classmethod
    def narration_fits_a_short(cls, value: str) -> str:
        word_count = len(value.split())
        if word_count < 75 or word_count > 130:
            raise ValueError("Narration must contain 75 to 130 words")
        return value


def _hashtag_for_phrase(value: str, *, max_words: int) -> str | None:
    without_parentheticals = re.sub(r"\([^)]*\)", "", value)
    words = [
        word for word in re.findall(r"[A-Za-z0-9]+", without_parentheticals) if word.lower() not in HASHTAG_STOP_WORDS
    ][:max_words]
    if not words:
        return None
    hashtag = "#" + "".join(word[:1].upper() + word[1:] for word in words)
    return hashtag[:50]


def case_hashtags(title: str, location: str | None) -> list[str]:
    hashtags: list[str] = []
    case_tag = _hashtag_for_phrase(title, max_words=4)
    location_tag = _hashtag_for_phrase(location, max_words=3) if location else None
    for hashtag in (case_tag, location_tag, "#CaseResearcher"):
        if hashtag and hashtag.casefold() not in {item.casefold() for item in hashtags}:
            hashtags.append(hashtag)
    return hashtags


def build_youtube_description(
    caption: str,
    source_urls: list[str],
    site_label: str,
    hashtags: list[str],
) -> str:
    source_lines = "\n".join(f"- {url}" for url in source_urls[:5])
    hashtag_line = " ".join(hashtags[:3])
    return (
        f"{caption}\n\n"
        f"Explore the full case at https://{site_label}\n\n"
        f"Sources:\n{source_lines}\n\n"
        "This video uses AI-generated narration and background visuals.\n\n"
        f"{hashtag_line}"
    )


def reel_slot(now: datetime) -> str:
    slot = "am" if now.hour < 12 else "pm"
    return f"youtube:{now.date().isoformat()}:{slot}"


def manual_reel_slot(now: datetime) -> str:
    return f"youtube:manual:{now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"


def music_track_for_slot(slot: str) -> Path:
    """Alternate the bundled tracks between consecutive twelve-hour slots."""
    date_text, period = slot.rsplit(":", 2)[-2:]
    if period in {"am", "pm"}:
        slot_number = datetime.fromisoformat(date_text).toordinal() * 2 + (period == "pm")
    else:
        slot_number = int.from_bytes(hashlib.sha256(slot.encode()).digest()[:8])
    return MUSIC_TRACKS[slot_number % len(MUSIC_TRACKS)]


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def build_srt(scene_texts: list[str], scene_durations: list[float]) -> str:
    if len(scene_texts) != len(scene_durations):
        raise ValueError("Each subtitle must have a matching scene duration")
    blocks = []
    start = 0.0
    for index, text in enumerate(scene_texts, start=1):
        end = start + scene_durations[index - 1]
        blocks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text.strip()}\n")
        start = end
    return "\n".join(blocks)


def split_narration(narration: str, scene_count: int) -> list[str]:
    """Partition legacy narration without losing or reordering words."""
    words = narration.split()
    return [
        " ".join(words[len(words) * index // scene_count : len(words) * (index + 1) // scene_count])
        for index in range(scene_count)
    ]


def build_scene_metadata(
    scene_texts: list[str],
    scene_prompts: list[str],
    scene_narrations: list[str],
    scene_durations: list[float],
) -> list[dict[str, object]]:
    scenes = []
    scene_start = 0.0
    for text, prompt, narration_text, duration in zip(
        scene_texts, scene_prompts, scene_narrations, scene_durations, strict=True
    ):
        scene_end = scene_start + duration
        scenes.append(
            {
                "start_second": round(scene_start),
                "end_second": round(scene_end),
                "on_screen_text": text,
                "visual_direction": prompt,
                "narration_text": narration_text,
            }
        )
        scene_start = scene_end
    return scenes


async def _run_process(*command: str) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        detail = stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(f"{Path(command[0]).name} failed: {detail}")
    return stdout


async def audio_duration(path: Path) -> float:
    output = await _run_process(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    )
    duration = float(output.decode().strip())
    if duration <= 0 or duration > 300:
        raise RuntimeError("Generated narration has an invalid duration")
    return duration


async def fit_narration_duration(
    audio_path: Path,
    scene_durations: list[float],
) -> tuple[Path, list[float]]:
    narration_seconds = sum(scene_durations)
    if narration_seconds <= MAX_NARRATION_SECONDS:
        return audio_path, scene_durations

    fitted_path = audio_path.with_name(f"{audio_path.stem}-fitted{audio_path.suffix}")
    tempo = narration_seconds / TARGET_NARRATION_SECONDS
    await _run_process(
        "ffmpeg",
        "-y",
        "-i",
        str(audio_path),
        "-filter:a",
        f"atempo={tempo:.8f}",
        "-vn",
        str(fitted_path),
    )
    fitted_seconds = await audio_duration(fitted_path)
    if fitted_seconds > MAX_NARRATION_SECONDS:
        raise RuntimeError("Generated narration could not be fitted to a Short")
    scale = fitted_seconds / narration_seconds
    return fitted_path, [duration * scale for duration in scene_durations]


async def render_vertical_video(
    directory: Path,
    visuals: list[SceneVisual],
    audio_segments: list[bytes],
    scene_texts: list[str],
    scene_prompts: list[str],
    scene_narrations: list[str],
    site_label: str,
    music_path: Path,
    music_volume: float,
) -> tuple[bytes, int, list[dict[str, object]]]:
    scene_count = len(visuals)
    if not (scene_count == len(audio_segments) == len(scene_texts) == len(scene_prompts) == len(scene_narrations)):
        raise ValueError("Every reel scene must have a visual, narration, caption, and prompt")
    if not await asyncio.to_thread(music_path.is_file):
        raise RuntimeError(f"Reel music track is missing: {music_path.name}")
    audio_path = directory / "narration.mp3"
    audio_paths = []
    for index, content in enumerate(audio_segments):
        path = directory / f"narration-{index}.mp3"
        path.write_bytes(content)
        audio_paths.append(path)
    concat_inputs = [part for path in audio_paths for part in ("-i", str(path))]
    concat_filter = "".join(f"[{index}:a]" for index in range(len(audio_paths)))
    await _run_process(
        "ffmpeg",
        "-y",
        *concat_inputs,
        "-filter_complex",
        f"{concat_filter}concat=n={len(audio_paths)}:v=0:a=1[outa]",
        "-map",
        "[outa]",
        str(audio_path),
    )
    visual_paths: list[tuple[Path, Literal["image", "video"]]] = []
    for index, visual in enumerate(visuals):
        extension = "mp4" if visual.kind == "video" else "webp"
        path = directory / f"scene-{index}.{extension}"
        path.write_bytes(visual.content)
        visual_paths.append((path, visual.kind))
    scene_durations = [await audio_duration(path) for path in audio_paths]
    audio_path, scene_durations = await fit_narration_duration(audio_path, scene_durations)
    narration_seconds = sum(scene_durations)
    total_seconds = narration_seconds + 4
    srt_path = directory / "captions.srt"
    srt_path.write_text(build_srt(scene_texts, scene_durations), encoding="utf-8")
    output_path = directory / "reel.mp4"

    inputs: list[str] = []
    for (path, kind), duration in zip(visual_paths, scene_durations, strict=True):
        if kind == "video":
            inputs.extend(["-stream_loop", "-1", "-i", str(path)])
        else:
            inputs.extend(["-loop", "1", "-t", f"{duration:.3f}", "-i", str(path)])
    inputs.extend(
        [
            "-f",
            "lavfi",
            "-t",
            "4",
            "-i",
            "color=c=0x0b1117:s=1080x1920:r=30",
            "-i",
            str(audio_path),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path),
        ]
    )
    filters = []
    video_labels = []
    for index, duration in enumerate(scene_durations):
        label = f"v{index}"
        filters.append(
            f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"setsar=1,fps=30,trim=duration={duration:.3f},setpts=PTS-STARTPTS[{label}]"
        )
        video_labels.append(f"[{label}]")
    end_index = len(visual_paths)
    filters.append(
        f"[{end_index}:v]drawtext=fontfile={FONT_PATH}:text='{site_label}':"
        "fontcolor=white:fontsize=62:x=(w-text_w)/2:y=(h-text_h)/2,"
        "drawtext=fontfile=" + FONT_PATH + ":text='Explore the full case':"
        "fontcolor=0xd5a64a:fontsize=34:x=(w-text_w)/2:y=(h-text_h)/2-90[vend]"
    )
    video_labels.append("[vend]")
    filters.append("".join(video_labels) + f"concat=n={len(video_labels)}:v=1:a=0[sequence]")
    escaped_srt = str(srt_path).replace("'", "\\'")
    filters.append(
        f"[sequence]subtitles='{escaped_srt}':force_style='FontName=DejaVu Sans,FontSize=18,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&HAA000000,BorderStyle=3,Outline=1,"
        "Shadow=0,Alignment=2,MarginV=150',"
        f"drawtext=fontfile={FONT_PATH}:text='AI-generated narration':fontcolor=white@0.72:"
        "fontsize=20:x=36:y=36[outv]"
    )
    narration_index = len(visual_paths) + 1
    music_index = narration_index + 1
    fade_start = max(0, total_seconds - 2)
    filters.extend(
        [
            f"[{narration_index}:a]apad=pad_dur=4[narration]",
            f"[{music_index}:a]atrim=0:{total_seconds:.3f},asetpts=PTS-STARTPTS,"
            f"volume={music_volume:.3f},afade=t=out:st={fade_start:.3f}:d=2[music]",
            "[narration][music]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[outa]",
        ]
    )
    await _run_process(
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-t",
        f"{total_seconds:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    )
    scenes = build_scene_metadata(scene_texts, scene_prompts, scene_narrations, scene_durations)
    scenes[-1]["end_second"] = round(narration_seconds)
    scenes.append(
        {
            "start_second": round(narration_seconds),
            "end_second": round(total_seconds),
            "on_screen_text": f"Explore the full case at {site_label}",
            "visual_direction": "Brand end card",
            "narration_text": "",
        }
    )
    return output_path.read_bytes(), round(total_seconds), scenes


class VertexVeoGenerator:
    def __init__(self, settings: Settings) -> None:
        from google import genai
        from google.genai import types

        project_id = settings.reel_video_project_id or settings.gcs_project_id
        if not project_id:
            raise RuntimeError("REEL_VIDEO_PROJECT_ID or GCS_PROJECT_ID is required for Vertex Veo")
        self.settings = settings
        self.types = types
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=settings.reel_video_location,
            http_options=types.HttpOptions(api_version="v1"),
        )

    def _generate(self, prompt: str) -> bytes:
        operation = self.client.models.generate_videos(
            model=self.settings.reel_video_model,
            source=self.types.GenerateVideosSource(prompt=prompt),
            config=self.types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=self.settings.reel_video_duration_seconds,
                generate_audio=False,
                number_of_videos=1,
                person_generation="dont_allow",
                resolution="720p",
                negative_prompt=VEO_NEGATIVE_PROMPT,
            ),
        )
        deadline = time.monotonic() + self.settings.reel_video_timeout_seconds
        while not operation.done:
            if time.monotonic() >= deadline:
                raise RuntimeError("Vertex Veo video generation timed out")
            time.sleep(self.settings.reel_video_poll_seconds)
            operation = self.client.operations.get(operation)
        result = operation.result
        generated = result.generated_videos if result is not None else None
        video = generated[0].video if generated else None
        video_bytes = video.video_bytes if video is not None else None
        if not video_bytes:
            reasons = result.rai_media_filtered_reasons if result is not None else None
            detail = f": {'; '.join(reasons)}" if reasons else ""
            raise RuntimeError(f"Vertex Veo returned no video{detail}")
        return cast(bytes, video_bytes)

    async def generate(self, prompt: str) -> bytes:
        return await asyncio.to_thread(self._generate, prompt)


async def generate_image_visual(client: AsyncOpenAI, settings: Settings, prompt: str) -> SceneVisual:
    result = await client.images.generate(
        model=settings.ai_image_model,
        prompt=prompt,
        size="1024x1536",
        quality="low",
        output_format="webp",
        n=1,
    )
    encoded = result.data[0].b64_json if result.data else None
    if not encoded:
        raise RuntimeError("OpenAI returned no reel background image")
    return SceneVisual(base64.b64decode(encoded), "image")


async def generate_scene_visuals(
    client: AsyncOpenAI,
    settings: Settings,
    prompts: list[str],
) -> list[SceneVisual]:
    if settings.reel_visual_provider == "openai_image":
        return [await generate_image_visual(client, settings, prompt) for prompt in prompts]

    generator = VertexVeoGenerator(settings)
    visuals: list[SceneVisual] = []
    for scene_number, prompt in enumerate(prompts, start=1):
        try:
            content = await generator.generate(prompt)
            visuals.append(SceneVisual(content, "video"))
        except Exception:
            if not settings.reel_video_fallback_to_image:
                raise
            logger.exception("scheduled_reel_veo_fallback", scene_number=scene_number)
            visuals.append(await generate_image_visual(client, settings, prompt))
    return visuals


class YouTubeUploader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return all(
            (
                self.settings.youtube_client_id,
                self.settings.youtube_client_secret,
                self.settings.youtube_refresh_token,
            )
        )

    async def upload(self, video: bytes, *, title: str, description: str) -> str:
        if not self.configured():
            raise RuntimeError("YouTube OAuth credentials are not configured")
        async with httpx.AsyncClient(timeout=180) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.youtube_client_id,
                    "client_secret": self.settings.youtube_client_secret,
                    "refresh_token": self.settings.youtube_refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            if self.settings.youtube_channel_id:
                try:
                    channel = await authorized_channel(access_token)
                except AppError as exc:
                    raise RuntimeError(exc.message) from exc
                if channel.id != self.settings.youtube_channel_id:
                    raise RuntimeError(
                        f"YouTube token belongs to {channel.title} ({channel.id}), "
                        f"not configured channel {self.settings.youtube_channel_id}"
                    )
            metadata = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "categoryId": self.settings.youtube_category_id,
                    "tags": ["case research", "case researcher", "true crime", "shorts"],
                },
                "status": {"privacyStatus": self.settings.youtube_privacy_status},
            }
            start = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params={"uploadType": "resumable", "part": "snippet,status"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Length": str(len(video)),
                    "X-Upload-Content-Type": "video/mp4",
                },
                content=json.dumps(metadata),
            )
            start.raise_for_status()
            upload_url = start.headers.get("Location")
            if not upload_url:
                raise RuntimeError("YouTube did not return a resumable upload URL")
            uploaded = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(video)),
                },
                content=video,
            )
            uploaded.raise_for_status()
            video_id = uploaded.json().get("id")
            if not isinstance(video_id, str) or not video_id:
                raise RuntimeError("YouTube upload returned no video ID")
            return video_id


async def select_case(
    db: AsyncSession,
    case_id: uuid.UUID | None = None,
) -> tuple[Case, CaseSummary, list[Source]] | None:
    already_used = exists(select(ReelDraft.id).where(ReelDraft.case_id == Case.id, ReelDraft.automated.is_(True)))
    has_sources = exists(select(Source.id).where(Source.case_id == Case.id))
    eligibility = [
        Case.privacy == "public",
        Case.status == "active",
        Case.ai_research_status == "complete",
        CaseSummary.is_current.is_(True),
        has_sources,
    ]
    if case_id is None:
        eligibility.append(~already_used)
    else:
        eligibility.append(Case.id == case_id)
    row = (
        await db.execute(
            select(Case, CaseSummary)
            .join(CaseSummary, CaseSummary.case_id == Case.id)
            .where(*eligibility)
            .order_by(Case.view_count.desc(), Case.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    case, summary = row
    sources = list(
        (await db.scalars(select(Source).where(Source.case_id == case.id).order_by(Source.position).limit(8))).all()
    )
    if not sources:
        return None
    return case, summary, sources


async def generate_script(
    client: AsyncOpenAI,
    settings: Settings,
    case: Case,
    summary: CaseSummary,
    sources: list[Source],
) -> GeneratedReelScript:
    catalog = "\n".join(f"[{index}] {source.title} — {source.url}" for index, source in enumerate(sources, 1))
    response = await client.responses.parse(
        model=settings.ai_text_model,
        instructions=(
            "Turn the supplied sourced case overview into a 35 to 55 second YouTube Short. Write 80 to 105 "
            "spoken words in a calm documentary voice. Start with a factual hook, distinguish confirmed facts "
            "from allegations, avoid graphic or sensational wording, and invite viewers to examine the full case. "
            "Do not add facts, names, dates, or accusations beyond the overview and source catalog. Create exactly "
            f"{settings.reel_image_count} consecutive scenes. Put the exact spoken words for each scene in "
            "narration_text, and make the top-level narration those scene narrations joined in order. Every visual "
            "prompt must visibly illustrate the specific fact, place, time period, or object discussed in that "
            "scene's narration_text; avoid generic crime imagery. Each prompt must describe one continuous portrait "
            "documentary shot with specific subject motion and restrained camera movement. Prompts must be cinematic, "
            "non-graphic, contain no readable text or logos, and must not recreate real people or imply that an "
            "AI-generated person is a real participant. The caption must disclose AI-generated narration."
        ),
        input=f"CASE\n{case.title}\n\nOVERVIEW\n{summary.body}\n\nSOURCES\n{catalog}",
        text_format=GeneratedReelScript,
    )
    script = response.output_parsed
    if script is None or len(script.scenes) != settings.reel_image_count:
        raise RuntimeError("OpenAI returned an invalid reel script")
    script.narration = " ".join(scene.narration_text.strip() for scene in script.scenes)
    GeneratedReelScript.narration_fits_a_short(script.narration)
    return script


async def run(
    *,
    dry_run: bool = False,
    skip_upload: bool = False,
    force_new: bool = False,
    case_id: uuid.UUID | None = None,
) -> None:
    settings = get_settings()
    if case_id is not None and not force_new:
        raise RuntimeError("A specific case requires --force-new")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for scheduled reels")
    if not dry_run and not skip_upload and not YouTubeUploader(settings).configured():
        raise RuntimeError("YouTube OAuth credentials are required for scheduled reel publishing")
    now = datetime.now(UTC)
    slot = manual_reel_slot(now) if force_new else reel_slot(now)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    item: ReelDraft | None = None
    try:
        async with session_factory() as db:
            existing = await db.scalar(select(ReelDraft).where(ReelDraft.scheduled_slot == slot))
            if existing is not None:
                if existing.status == "published" or dry_run:
                    logger.info("scheduled_reel_slot_already_claimed", slot=slot, status=existing.status)
                    return
                case = await db.get(Case, existing.case_id)
                if case is None:
                    raise RuntimeError("Scheduled reel case no longer exists")
                sources = list(
                    (
                        await db.scalars(
                            select(Source).where(Source.case_id == case.id).order_by(Source.position).limit(8)
                        )
                    ).all()
                )
                legacy_narration = split_narration(existing.narration, len(existing.scenes))
                script = GeneratedReelScript(
                    title=existing.title,
                    hook=existing.hook,
                    narration=existing.narration,
                    caption=existing.caption,
                    scenes=[
                        GeneratedReelScene(
                            narration_text=str(scene.get("narration_text") or legacy_narration[index]),
                            on_screen_text=str(scene["on_screen_text"]),
                            image_prompt=str(scene["visual_direction"]),
                        )
                        for index, scene in enumerate(existing.scenes)
                    ],
                )
                item = existing
                item.status = "generating"
                item.error_message = None
                await db.commit()
                logger.info("scheduled_reel_resuming", slot=slot, reel_id=str(item.id))
            else:
                selected = await select_case(db, case_id)
                if selected is None:
                    logger.info("scheduled_reel_no_eligible_case", slot=slot)
                    return
                case, summary, sources = selected
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                script = await generate_script(client, settings, case, summary, sources)
                if dry_run:
                    logger.info("scheduled_reel_preview", case_id=str(case.id), title=script.title)
                    return
                scene_span = 45 // len(script.scenes)
                item = ReelDraft(
                    case_id=case.id,
                    created_by_user_id=case.created_by_user_id,
                    status="generating",
                    automated=True,
                    scheduled_slot=slot,
                    title=script.title,
                    hook=script.hook,
                    narration=script.narration,
                    caption=script.caption,
                    duration_seconds=45,
                    scenes=[
                        {
                            "start_second": index * scene_span,
                            "end_second": (index + 1) * scene_span if index < len(script.scenes) - 1 else 45,
                            "narration_text": scene.narration_text,
                            "on_screen_text": scene.on_screen_text,
                            "visual_direction": scene.image_prompt,
                        }
                        for index, scene in enumerate(script.scenes)
                    ],
                    sources=[{"title": source.title, "url": source.url} for source in sources],
                )
                db.add(item)
                try:
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    logger.info("scheduled_reel_slot_claimed_concurrently", slot=slot)
                    return

            client = AsyncOpenAI(api_key=settings.openai_api_key)

            try:
                visuals = await generate_scene_visuals(
                    client,
                    settings,
                    [scene.image_prompt for scene in script.scenes],
                )
                speech_segments = []
                for scene in script.scenes:
                    speech = await client.audio.speech.create(
                        model=settings.ai_speech_model,
                        voice=settings.ai_speech_voice,
                        input=scene.narration_text,
                        instructions=(
                            "Calm, clear documentary narration. Respectful, measured, and never sensational."
                        ),
                        response_format="mp3",
                    )
                    speech_segments.append(speech.content)
                item.status = "rendering"
                await db.commit()
                with tempfile.TemporaryDirectory(prefix="case-theory-reel-") as temp_name:
                    video, duration, scenes = await render_vertical_video(
                        Path(temp_name),
                        visuals,
                        speech_segments,
                        [scene.on_screen_text for scene in script.scenes],
                        [scene.image_prompt for scene in script.scenes],
                        [scene.narration_text for scene in script.scenes],
                        settings.reel_site_label,
                        music_track_for_slot(slot),
                        settings.reel_music_volume,
                    )
                object_key = f"reels/{item.id}/video.mp4"
                await get_storage_provider().put(object_key, video, "video/mp4")
                item.video_object_key = object_key
                item.duration_seconds = duration
                item.scenes = scenes
                if skip_upload:
                    item.status = "approved"
                    await db.commit()
                    logger.info("scheduled_reel_rendered", reel_id=str(item.id), object_key=object_key)
                    return
                item.status = "uploading"
                await db.commit()
                description = build_youtube_description(
                    script.caption,
                    [source.url for source in sources],
                    settings.reel_site_label,
                    case_hashtags(case.title, case.location),
                )
                video_id = await YouTubeUploader(settings).upload(
                    video,
                    title=script.title,
                    description=description,
                )
                item.status = "published"
                item.youtube_video_id = video_id
                item.youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                item.published_at = utc_now()
                await db.commit()
                logger.info(
                    "scheduled_reel_published",
                    reel_id=str(item.id),
                    case_id=str(case.id),
                    youtube_video_id=video_id,
                )
            except Exception as exc:
                await db.rollback()
                failed = await db.get(ReelDraft, item.id)
                if failed is not None:
                    failed.status = "failed"
                    failed.error_message = str(exc)[:1000]
                    await db.commit()
                raise
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and publish one scheduled YouTube Short")
    parser.add_argument("--dry-run", action="store_true", help="Generate the script without storing or rendering it")
    parser.add_argument("--skip-upload", action="store_true", help="Render and store the MP4 without uploading it")
    parser.add_argument(
        "--force-new",
        action="store_true",
        help="Use a unique manual slot instead of the current scheduled slot",
    )
    parser.add_argument("--case-id", type=uuid.UUID, help="Generate the Short for this eligible case")
    arguments = parser.parse_args()
    asyncio.run(
        run(
            dry_run=arguments.dry_run,
            skip_upload=arguments.skip_upload,
            force_new=arguments.force_new,
            case_id=arguments.case_id,
        )
    )


if __name__ == "__main__":
    main()
