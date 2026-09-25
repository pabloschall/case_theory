import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.cases.schemas import SourceRead
from app.evidence.schemas import EvidenceRead
from app.people.schemas import LinkedPersonRead

ReactionEmoji = Literal["👍", "❤️", "🤔", "🔎", "❓"]
ThreadType = Literal["question", "theory", "evidence", "dispute"]


class ThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=1, max_length=5000)
    thread_type: ThreadType = "question"
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    person_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text cannot be blank")
        return normalized


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=3000)

    @field_validator("body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Comment cannot be blank")
        return normalized


class ReactionToggle(BaseModel):
    emoji: ReactionEmoji


class AuthorRead(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str


class ReactionRead(BaseModel):
    emoji: ReactionEmoji
    count: int
    reacted_by_me: bool


class CommentRead(BaseModel):
    id: uuid.UUID
    body: str
    author: AuthorRead
    created_at: datetime
    reactions: list[ReactionRead]


class ThreadRead(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    thread_type: ThreadType
    author: AuthorRead
    created_at: datetime
    updated_at: datetime
    comments: list[CommentRead]
    evidence: list[EvidenceRead]
    people: list[LinkedPersonRead]
    sources: list[SourceRead]
    ai_generated: bool
    review_status: str
    vote_count: int
    voted_by_me: bool


class ThreadVoteRead(BaseModel):
    vote_count: int
    voted_by_me: bool


class ThreadPage(BaseModel):
    items: list[ThreadRead]
    next_cursor: uuid.UUID | None
    has_more: bool
    total: int
    active_count: int
    source_link_count: int
    comment_count: int
