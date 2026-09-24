import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.cases.models import Source, TimelineEvent
    from app.discussions.models import DiscussionThread
    from app.users.models import User


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_case_created_id", "case_id", "created_at", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(30))
    storage_object_key: Mapped[str | None] = mapped_column(String(1024), unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(150))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), index=True
    )
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    visibility: Mapped[str] = mapped_column(String(30), default="case")
    processing_status: Mapped[str] = mapped_column(String(30), default="pending")
    ai_generated: Mapped[bool] = mapped_column(default=False, server_default="false")
    review_status: Mapped[str] = mapped_column(String(30), default="published", server_default="published")
    moderation_status: Mapped[str] = mapped_column(
        String(30), default="visible", server_default="visible", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    discussion_links: Mapped[list["DiscussionThreadEvidence"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )
    timeline_links: Mapped[list["TimelineEventEvidence"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )
    source: Mapped["Source | None"] = relationship()
    comments: Mapped[list["EvidenceComment"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )


class EvidenceComment(Base):
    __tablename__ = "evidence_comments"
    __table_args__ = (
        Index("ix_evidence_comments_evidence_created_id", "evidence_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    moderation_status: Mapped[str] = mapped_column(
        String(30), default="visible", server_default="visible", index=True
    )

    evidence: Mapped[Evidence] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()


class DiscussionThreadEvidence(Base):
    __tablename__ = "discussion_thread_evidence"
    __table_args__ = (UniqueConstraint("thread_id", "evidence_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discussion_threads.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    thread: Mapped["DiscussionThread"] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship(back_populates="discussion_links")


class TimelineEventEvidence(Base):
    __tablename__ = "timeline_event_evidence"
    __table_args__ = (UniqueConstraint("timeline_event_id", "evidence_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    timeline_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timeline_events.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    timeline_event: Mapped["TimelineEvent"] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship(back_populates="timeline_links")
