import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_status_created_id", "status", "created_at", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(40), index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(index=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    target_summary: Mapped[str] = mapped_column(Text)
    reason_code: Mapped[str] = mapped_column(String(40), index=True)
    details: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="RESTRICT"), index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    action: Mapped[str] = mapped_column(String(40), index=True)
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[uuid.UUID] = mapped_column()
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
