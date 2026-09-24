import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotebookNoteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=20_000)

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note text cannot be blank")
        return normalized


class ContributorAuthorRead(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str


class NotebookNoteRead(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    body: str
    author: ContributorAuthorRead
    can_edit: bool
    created_at: datetime
    updated_at: datetime


class NotebookNotePage(BaseModel):
    items: list[NotebookNoteRead]
    next_cursor: uuid.UUID | None
    has_more: bool
    total: int


class TimelineEntryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_on: date
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=20_000)

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Timeline text cannot be blank")
        return normalized


class TimelineEntryRead(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    occurred_on: date
    title: str
    body: str
    author: ContributorAuthorRead
    can_edit: bool
    created_at: datetime
    updated_at: datetime
