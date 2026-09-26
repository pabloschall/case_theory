import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RankRead(BaseModel):
    code: str
    name: str
    threshold: int
    icon_key: str


class BadgeRead(BaseModel):
    code: str
    name: str
    description: str
    criteria: str
    category: str
    icon_key: str
    earned_at: datetime | None


class XpReceiptRead(BaseModel):
    id: uuid.UUID
    xp: int
    reason: str
    created_at: datetime


class ProgressionSummary(BaseModel):
    lifetime_xp: int
    show_rank: bool
    show_badges: bool
    rank: RankRead
    next_rank: RankRead | None
    progress_percent: int
    xp_to_next_rank: int | None
    badges: list[BadgeRead]
    pending_badges: list[BadgeRead]
    pending_receipts: list[XpReceiptRead]


class LedgerEntryRead(BaseModel):
    id: uuid.UUID
    rule_code: str
    xp: int
    reason: str
    resource_type: str | None
    resource_id: str | None
    created_at: datetime


class LedgerPage(BaseModel):
    items: list[LedgerEntryRead]
    page: int
    page_size: int
    total: int
    total_pages: int


class ProgressionAcknowledge(BaseModel):
    receipt_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    badge_codes: list[str] = Field(default_factory=list, max_length=20)


class ProgressionPrivacyUpdate(BaseModel):
    show_rank: bool
    show_badges: bool
