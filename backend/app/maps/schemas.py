import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.evidence.schemas import EvidenceRead
from app.people.schemas import LinkedPersonRead

LocationType = Literal[
    "primary",
    "event",
    "evidence",
    "last_seen",
    "sighting",
    "search_area",
    "law_enforcement",
    "other",
]
Precision = Literal["exact", "approximate"]
VerificationStatus = Literal["verified", "source_backed", "unverified", "disputed"]
ReviewStatus = Literal["suggested", "confirmed", "rejected"]


class LocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=3, max_length=3000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_type: LocationType = "other"
    occurred_on: date | None = None
    precision: Precision = "approximate"
    verification_status: VerificationStatus = "unverified"
    source_id: uuid.UUID | None = None
    source_url: HttpUrl | None = None
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    person_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def normalize(self) -> "LocationCreate":
        self.name = self.name.strip()
        self.description = self.description.strip()
        return self


class LocationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=240)
    description: str | None = Field(default=None, min_length=3, max_length=3000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_type: LocationType | None = None
    occurred_on: date | None = None
    precision: Precision | None = None
    verification_status: VerificationStatus | None = None
    source_id: uuid.UUID | None = None
    source_url: HttpUrl | None = None
    review_status: ReviewStatus | None = None


class LocationRead(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    name: str
    description: str
    latitude: float | None
    longitude: float | None
    location_type: LocationType
    occurred_on: date | None
    precision: Precision
    verification_status: VerificationStatus
    source_id: uuid.UUID | None
    source_url: str | None
    source_title: str | None
    ai_suggested: bool
    review_status: ReviewStatus
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    evidence: list[EvidenceRead]
    people: list[LinkedPersonRead]
