import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.cases.models import Source
    from app.evidence.models import Evidence
    from app.people.models import Person


class CaseLocation(Base):
    __tablename__ = "case_locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    location_type: Mapped[str] = mapped_column(String(40), default="other", index=True)
    occurred_on: Mapped[date | None] = mapped_column(Date, index=True)
    precision: Mapped[str] = mapped_column(String(30), default="approximate")
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    ai_suggested: Mapped[bool] = mapped_column(default=False)
    review_status: Mapped[str] = mapped_column(String(30), default="confirmed")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    source: Mapped["Source | None"] = relationship()
    evidence_links: Mapped[list["CaseLocationEvidence"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )
    person_links: Mapped[list["CaseLocationPerson"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )


class CaseLocationEvidence(Base):
    __tablename__ = "case_location_evidence"
    __table_args__ = (UniqueConstraint("location_id", "evidence_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("case_locations.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    location: Mapped[CaseLocation] = relationship(back_populates="evidence_links")
    evidence: Mapped["Evidence"] = relationship()


class CaseLocationPerson(Base):
    __tablename__ = "case_location_people"
    __table_args__ = (UniqueConstraint("location_id", "person_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("case_locations.id", ondelete="CASCADE"), index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    location: Mapped[CaseLocation] = relationship(back_populates="person_links")
    person: Mapped["Person"] = relationship()
