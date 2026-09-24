import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.evidence.schemas import EvidenceRead

PersonCategory = Literal["primary", "family", "friend", "law_enforcement", "witness", "other"]
EntityType = Literal["person", "organization", "location", "other"]
ReviewStatus = Literal["suggested", "confirmed", "rejected"]


class PersonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=240)
    role: str = Field(min_length=2, max_length=120)
    category: PersonCategory = "other"
    entity_type: EntityType = "person"
    photo_url: HttpUrl | None = None
    date_of_birth: date | None = None
    place_of_birth: str | None = Field(default=None, max_length=300)
    relationship_to_primary: str | None = Field(default=None, max_length=240)
    summary: str | None = Field(default=None, max_length=5000)
    is_primary: bool = False

    @field_validator("name", "role")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()


class PersonPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=240)
    role: str | None = Field(default=None, min_length=2, max_length=120)
    category: PersonCategory | None = None
    entity_type: EntityType | None = None
    photo_url: HttpUrl | None = None
    date_of_birth: date | None = None
    place_of_birth: str | None = Field(default=None, max_length=300)
    relationship_to_primary: str | None = Field(default=None, max_length=240)
    summary: str | None = Field(default=None, max_length=5000)
    is_primary: bool | None = None
    review_status: ReviewStatus | None = None


class PersonRead(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    name: str
    slug: str
    role: str
    category: PersonCategory
    entity_type: EntityType
    photo_url: str | None
    date_of_birth: date | None
    place_of_birth: str | None
    relationship_to_primary: str | None
    summary: str | None
    is_primary: bool
    ai_suggested: bool
    review_status: ReviewStatus
    connection_count: int
    evidence_count: int
    notes_count: int
    created_at: datetime
    updated_at: datetime


class LinkedPersonRead(BaseModel):
    """Compact person representation embedded in case objects."""

    id: uuid.UUID
    name: str
    role: str
    category: PersonCategory
    entity_type: EntityType
    photo_url: str | None


class RelationshipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_person_id: uuid.UUID
    target_person_id: uuid.UUID
    relationship_type: str = Field(min_length=2, max_length=50)
    label: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=3000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_type: str | None = Field(default=None, max_length=40)
    source_id: uuid.UUID | None = None
    source_url: HttpUrl | None = None
    ai_suggested: bool = False

    @model_validator(mode="after")
    def distinct_people(self) -> "RelationshipCreate":
        if self.source_person_id == self.target_person_id:
            raise ValueError("A relationship must connect two different entities")
        return self


class RelationshipPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationship_type: str | None = Field(default=None, min_length=2, max_length=50)
    label: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=3000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_type: str | None = Field(default=None, max_length=40)
    source_id: uuid.UUID | None = None
    source_url: HttpUrl | None = None
    review_status: ReviewStatus | None = None


class RelationshipRead(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    source_person_id: uuid.UUID
    target_person_id: uuid.UUID
    relationship_type: str
    label: str
    description: str | None
    confidence: float | None
    source_type: str | None
    source_id: uuid.UUID | None
    source_url: str | None
    source_title: str | None
    ai_suggested: bool
    review_status: ReviewStatus
    created_at: datetime
    updated_at: datetime


class PersonNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note cannot be blank")
        return normalized


class PersonNoteRead(BaseModel):
    id: uuid.UUID
    body: str
    author_user_id: uuid.UUID
    author_name: str
    created_at: datetime
    updated_at: datetime


class PersonEvidenceRead(BaseModel):
    evidence: EvidenceRead
