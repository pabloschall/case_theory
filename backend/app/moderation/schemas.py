import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReportResource = Literal["discussion_comment", "evidence_comment", "evidence", "user"]
ReportReason = Literal[
    "harassment",
    "hate_speech",
    "doxxing",
    "illegal_material",
    "misinformation",
    "spam",
    "other",
]
ModerationDecision = Literal["hide", "restore", "lock_user", "unlock_user", "resolve", "dismiss"]


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_type: ReportResource
    resource_id: uuid.UUID
    reason_code: ReportReason
    details: str = Field(min_length=10, max_length=3000)

    @field_validator("details")
    @classmethod
    def strip_details(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("Please provide at least 10 characters of detail")
        return stripped


class ReportRead(BaseModel):
    id: uuid.UUID
    reporter_user_id: uuid.UUID
    reporter_email: str
    resource_type: str
    resource_id: uuid.UUID
    target_user_id: uuid.UUID | None
    target_summary: str
    reason_code: str
    details: str
    status: str
    resolution_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class ReportPage(BaseModel):
    items: list[ReportRead]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ModerationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: ModerationDecision
    note: str | None = Field(default=None, max_length=2000)
