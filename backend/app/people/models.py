import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.cases.models import Source, TimelineEvent
    from app.discussions.models import DiscussionThread
    from app.evidence.models import Evidence
    from app.users.models import User


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("case_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    slug: Mapped[str] = mapped_column(String(280))
    role: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(30), default="other", index=True)
    entity_type: Mapped[str] = mapped_column(String(30), default="person")
    photo_url: Mapped[str | None] = mapped_column(String(2048))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    place_of_birth: Mapped[str | None] = mapped_column(String(300))
    relationship_to_primary: Mapped[str | None] = mapped_column(String(240))
    summary: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(default=False)
    ai_suggested: Mapped[bool] = mapped_column(default=False)
    review_status: Mapped[str] = mapped_column(String(30), default="confirmed")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    evidence_links: Mapped[list["PersonEvidence"]] = relationship(back_populates="person", cascade="all, delete-orphan")
    notes: Mapped[list["PersonNote"]] = relationship(
        back_populates="person", cascade="all, delete-orphan", order_by="PersonNote.created_at.desc()"
    )


class PersonRelationship(Base):
    __tablename__ = "person_relationships"
    __table_args__ = (UniqueConstraint("source_person_id", "target_person_id", "relationship_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    source_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    target_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_type: Mapped[str | None] = mapped_column(String(40))
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    ai_suggested: Mapped[bool] = mapped_column(default=False)
    review_status: Mapped[str] = mapped_column(String(30), default="confirmed")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    source: Mapped["Source | None"] = relationship()


class PersonEvidence(Base):
    __tablename__ = "person_evidence"
    __table_args__ = (UniqueConstraint("person_id", "evidence_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    person: Mapped[Person] = relationship(back_populates="evidence_links")
    evidence: Mapped["Evidence"] = relationship()


class TimelineEventPerson(Base):
    __tablename__ = "timeline_event_people"
    __table_args__ = (UniqueConstraint("timeline_event_id", "person_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    timeline_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timeline_events.id", ondelete="CASCADE"), index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    timeline_event: Mapped["TimelineEvent"] = relationship(back_populates="person_links")
    person: Mapped[Person] = relationship()


class DiscussionThreadPerson(Base):
    __tablename__ = "discussion_thread_people"
    __table_args__ = (UniqueConstraint("thread_id", "person_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discussion_threads.id", ondelete="CASCADE"), index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    thread: Mapped["DiscussionThread"] = relationship(back_populates="person_links")
    person: Mapped[Person] = relationship()


class PersonNote(Base):
    __tablename__ = "person_notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    person: Mapped[Person] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship()
