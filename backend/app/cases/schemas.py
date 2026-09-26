import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.evidence.schemas import EvidenceRead
from app.people.schemas import LinkedPersonRead


class CaseCreate(BaseModel):
    victim_names: str = Field(min_length=2, max_length=500)
    year: int | None = Field(default=None, ge=1800, le=2100)
    location: str | None = Field(default=None, max_length=300)
    additional_context: str | None = Field(default=None, max_length=4000)
    creation_mode: Literal["ai", "manual"] = "ai"
    summary: str | None = Field(default=None, max_length=12000)
    banner_template: Literal[
        "/case-banners/mountain-trail.jpg",
        "/case-banners/coastal-road.jpg",
        "/case-banners/rainy-city.jpg",
        "/case-banners/desert-road.jpg",
        "/case-banners/archive-room.jpg",
    ] | None = None
    privacy: Literal["public", "private"] = "public"

    @field_validator("location")
    @classmethod
    def normalize_optional_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("summary")
    @classmethod
    def normalize_optional_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_manual_fields(self) -> "CaseCreate":
        if self.creation_mode == "manual":
            if self.summary is None or len(self.summary) < 20:
                raise ValueError("Manual cases need a summary of at least 20 characters")
            if self.banner_template is None:
                raise ValueError("Select a banner template for a manual case")
        return self


class SummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    body: str
    source: str
    ai_model: str | None


class CaseOwnerRead(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str


class PrivacyPatch(BaseModel):
    privacy: Literal["public", "private"]


class FollowState(BaseModel):
    is_following: bool


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    url: str
    publisher: str | None
    source_type: str
    retrieved_at: datetime


class CaseSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: str
    external_id: str
    source_url: str
    source_name: str
    source_published_at: datetime | None
    source_updated_at: datetime | None


class TimelineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    date_label: str
    occurred_on: date | None
    occurred_time: time | None
    position: int | None
    date_precision: str
    title: str
    description: str
    verification_status: str
    confidence: str
    source_note: str
    ai_generated: bool
    created_by_user_id: uuid.UUID | None
    sources: list[SourceRead]
    evidence: list[EvidenceRead]
    people: list[LinkedPersonRead]


class TimelineEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_on: date
    occurred_time: time | None = None
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=1, max_length=5000)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    person_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)

    @field_validator("title", "description")
    @classmethod
    def normalize_timeline_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text cannot be blank")
        return normalized


class TimelineOrderUpdate(BaseModel):
    event_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)

    @field_validator("event_ids")
    @classmethod
    def require_unique_events(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Timeline event IDs must be unique")
        return value


class CaseRead(BaseModel):
    id: uuid.UUID
    public_id: uuid.UUID
    slug: str
    title: str
    victim_names: str
    year: int | None
    location: str | None
    status: str
    privacy: str
    owner: CaseOwnerRead
    is_owner: bool
    is_following: bool
    ai_research_status: str
    ai_error_message: str | None
    cover_image_url: str | None
    summary: SummaryRead | None
    timeline: list[TimelineEventRead]
    sources: list[SourceRead]
    external_sources: list[CaseSourceRead]
    created_at: datetime


class CaseListItem(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    victim_names: str
    year: int | None
    location: str | None
    privacy: str
    is_owner: bool
    is_following: bool
    ai_research_status: str
    cover_image_url: str | None
    discussion_count: int
    created_at: datetime
    updated_at: datetime


class CaseListPage(BaseModel):
    items: list[CaseListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class AdminCaseListItem(CaseListItem):
    status: str
    privacy: str
