import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base
from app.users.models import User

if TYPE_CHECKING:
    from app.cases.models import Source
    from app.evidence.models import DiscussionThreadEvidence
    from app.people.models import DiscussionThreadPerson


class DiscussionThread(Base):
    __tablename__ = "discussion_threads"
    __table_args__ = (
        Index("ix_discussion_threads_case_updated_id", "case_id", "updated_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    body: Mapped[str] = mapped_column(Text)
    thread_type: Mapped[str] = mapped_column(String(24), default="question", server_default="question")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    ai_generated: Mapped[bool] = mapped_column(default=False, server_default="false")
    review_status: Mapped[str] = mapped_column(String(30), default="published", server_default="published")

    author: Mapped[User] = relationship()
    comments: Mapped[list["DiscussionComment"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="DiscussionComment.created_at"
    )
    evidence_links: Mapped[list["DiscussionThreadEvidence"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    person_links: Mapped[list["DiscussionThreadPerson"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    source_links: Mapped[list["DiscussionThreadSource"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    votes: Mapped[list["DiscussionThreadVote"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )


class DiscussionThreadVote(Base):
    __tablename__ = "discussion_thread_votes"
    __table_args__ = (UniqueConstraint("thread_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discussion_threads.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    thread: Mapped[DiscussionThread] = relationship(back_populates="votes")


class DiscussionThreadSource(Base):
    __tablename__ = "discussion_thread_sources"
    __table_args__ = (UniqueConstraint("thread_id", "source_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discussion_threads.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    thread: Mapped[DiscussionThread] = relationship(back_populates="source_links")
    source: Mapped["Source"] = relationship()


class DiscussionComment(Base):
    __tablename__ = "discussion_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discussion_threads.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    moderation_status: Mapped[str] = mapped_column(
        String(30), default="visible", server_default="visible", index=True
    )

    thread: Mapped[DiscussionThread] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()
    reactions: Mapped[list["DiscussionReaction"]] = relationship(
        back_populates="comment", cascade="all, delete-orphan"
    )


class DiscussionReaction(Base):
    __tablename__ = "discussion_reactions"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", "emoji"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discussion_comments.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    emoji: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    comment: Mapped[DiscussionComment] = relationship(back_populates="reactions")
