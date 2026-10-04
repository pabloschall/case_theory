import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.evidence.models import TimelineEventEvidence
    from app.people.models import TimelineEventPerson
    from app.users.models import User


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    public_id: Mapped[uuid.UUID] = mapped_column(unique=True, index=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    victim_names: Mapped[str] = mapped_column(String(500))
    year: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(300))
    intake_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    privacy: Mapped[str] = mapped_column(String(30), default="public")
    ai_research_status: Mapped[str] = mapped_column(String(30), default="queued")
    ai_error_message: Mapped[str | None] = mapped_column(String(500))
    cover_image_url: Mapped[str | None] = mapped_column(String(2048))
    cover_image_object_key: Mapped[str | None] = mapped_column(String(1024))
    cover_image_prompt: Mapped[str | None] = mapped_column(Text)
    view_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    counts_toward_weekly_limit: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    summaries: Mapped[list["CaseSummary"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    timeline: Mapped[list["TimelineEvent"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    sources: Mapped[list["Source"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    external_sources: Mapped[list["CaseSource"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    owner: Mapped["User"] = relationship(foreign_keys=[created_by_user_id])


class CaseFollower(Base):
    __tablename__ = "case_followers"
    __table_args__ = (UniqueConstraint("case_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CaseMember(Base):
    __tablename__ = "case_members"
    __table_args__ = (UniqueConstraint("case_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="contributor")
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CaseSummary(Base):
    __tablename__ = "case_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), default="ai")
    ai_model: Mapped[str | None] = mapped_column(String(100))
    is_current: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    case: Mapped[Case] = relationship(back_populates="summaries")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    date_label: Mapped[str] = mapped_column(String(120))
    occurred_on: Mapped[date | None] = mapped_column(Date, index=True)
    occurred_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_precision: Mapped[str] = mapped_column(String(30), default="unknown")
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(30), default="ai_suggested")
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    source_note: Mapped[str] = mapped_column(String(500), default="Based only on user-provided case intake")
    ai_generated: Mapped[bool] = mapped_column(default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    case: Mapped[Case] = relationship(back_populates="timeline")
    source_links: Mapped[list["TimelineEventSource"]] = relationship(
        back_populates="timeline_event", cascade="all, delete-orphan"
    )
    evidence_links: Mapped[list["TimelineEventEvidence"]] = relationship(
        back_populates="timeline_event", cascade="all, delete-orphan"
    )
    person_links: Mapped[list["TimelineEventPerson"]] = relationship(
        back_populates="timeline_event", cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("case_id", "canonical_url"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer)
    publisher: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(40), default="other")
    reliability_metadata: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    case: Mapped[Case] = relationship(back_populates="sources")


class CaseSource(Base):
    """Immutable upstream source layer, kept separate from community edits."""

    __tablename__ = "case_sources"
    __table_args__ = (UniqueConstraint("source_type", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    source_name: Mapped[str] = mapped_column(String(255))
    source_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
    )
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    case: Mapped[Case] = relationship(back_populates="external_sources")
    citations: Mapped[list["SourceCitation"]] = relationship(
        back_populates="case_source", cascade="all, delete-orphan"
    )


class SourceCitation(Base):
    """Field-level provenance for official and generated case artifacts."""

    __tablename__ = "source_citations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("case_sources.id", ondelete="CASCADE"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(50), index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(index=True)
    source_field: Mapped[str] = mapped_column(String(120))
    source_text: Mapped[str | None] = mapped_column(Text)
    interpretation_type: Mapped[str] = mapped_column(String(30), default="official")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    case_source: Mapped[CaseSource] = relationship(back_populates="citations")


class TimelineEventSource(Base):
    __tablename__ = "timeline_event_sources"
    __table_args__ = (UniqueConstraint("timeline_event_id", "source_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    timeline_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timeline_events.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    timeline_event: Mapped[TimelineEvent] = relationship(back_populates="source_links")
    source: Mapped[Source] = relationship()


class CaseGenerationJob(Base):
    __tablename__ = "case_generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    text_model: Mapped[str | None] = mapped_column(String(100))
    image_model: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
