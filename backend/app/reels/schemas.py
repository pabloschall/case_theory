import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator, model_validator


class ReelScene(BaseModel):
    start_second: int = Field(ge=0, le=180)
    end_second: int = Field(gt=0, le=180)
    on_screen_text: str = Field(min_length=1, max_length=180)
    visual_direction: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def end_follows_start(self) -> "ReelScene":
        if self.end_second <= self.start_second:
            raise ValueError("Scene end must follow its start")
        return self


class ReelSource(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=8, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return str(TypeAdapter(HttpUrl).validate_python(value))


class ReelDraftCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    hook: str = Field(min_length=3, max_length=280)
    narration: str = Field(min_length=20, max_length=5000)
    caption: str = Field(min_length=1, max_length=2200)
    duration_seconds: int = Field(ge=15, le=60)
    scenes: list[ReelScene] = Field(min_length=2, max_length=12)
    sources: list[ReelSource] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_timeline(self) -> "ReelDraftCreate":
        if self.scenes[0].start_second != 0:
            raise ValueError("The first scene must start at zero")
        previous_end = 0
        for scene in self.scenes:
            if scene.start_second != previous_end:
                raise ValueError("Scenes must be contiguous")
            previous_end = scene.end_second
        if previous_end != self.duration_seconds:
            raise ValueError("The final scene must end at the reel duration")
        return self


class ReelDraftUpdate(ReelDraftCreate):
    status: Literal["draft", "approved"]


class ReelDraftRead(ReelDraftCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    created_by_user_id: uuid.UUID
    status: Literal["draft", "approved", "generating", "rendering", "uploading", "published", "failed"]
    automated: bool
    video_object_key: str | None
    youtube_video_id: str | None
    youtube_url: str | None
    error_message: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
