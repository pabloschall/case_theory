import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

EvidenceType = Literal["document", "image", "video", "audio", "link", "article", "other"]


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    evidence_type: str
    original_filename: str | None
    mime_type: str | None
    file_size: int | None
    source_url: str | None
    source_id: uuid.UUID | None
    verification_status: str
    processing_status: str
    ai_generated: bool
    review_status: str
    comment_count: int = 0
    created_at: datetime


class EvidencePage(BaseModel):
    items: list[EvidenceRead]
    next_cursor: uuid.UUID | None
    has_more: bool
    total: int


class ExternalEvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=3000)
    url: HttpUrl
    evidence_type: EvidenceType = "link"

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip()


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=3000)
    filename: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=3, max_length=150)
    file_size: int = Field(gt=0)

    @field_validator("title", "filename", "content_type")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return value.strip()


class UploadTicket(BaseModel):
    evidence: EvidenceRead
    upload_url: str
    upload_method: Literal["POST", "PUT"]
    upload_headers: dict[str, str]


class EvidenceUrl(BaseModel):
    url: str


class EvidenceLinkRequest(BaseModel):
    evidence_id: uuid.UUID


class EvidenceCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=3000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Comment cannot be empty")
        return normalized


class EvidenceCommentAuthor(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str


class EvidenceCommentRead(BaseModel):
    id: uuid.UUID
    body: str
    author: EvidenceCommentAuthor
    can_delete: bool
    created_at: datetime
    updated_at: datetime


class EvidenceCommentPage(BaseModel):
    items: list[EvidenceCommentRead]
    next_cursor: uuid.UUID | None
    has_more: bool
    total: int
