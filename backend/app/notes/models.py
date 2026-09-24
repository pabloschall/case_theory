import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base
from app.users.models import User


class CaseNotebookNote(Base):
    __tablename__ = "case_notebook_notes"
    __table_args__ = (
        Index(
            "ix_case_notebook_notes_case_updated_id",
            "case_id",
            "updated_at",
            "id",
        ),
        Index(
            "ix_case_notebook_notes_owner_case_updated_id",
            "author_user_id",
            "case_id",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    author: Mapped[User] = relationship(foreign_keys=[author_user_id])


class CaseTimelineEntry(Base):
    __tablename__ = "case_timeline_entries"
    __table_args__ = (
        Index(
            "ix_case_timeline_entries_case_date_id",
            "case_id",
            "occurred_on",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    occurred_on: Mapped[date] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    author: Mapped[User] = relationship(foreign_keys=[author_user_id])
