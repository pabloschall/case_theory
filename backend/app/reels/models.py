import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.cases.models import Case
from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base
from app.users.models import User


class ReelDraft(Base):
    __tablename__ = "reel_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="draft")
    automated: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_slot: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    hook: Mapped[str] = mapped_column(String(280))
    narration: Mapped[str] = mapped_column(Text)
    caption: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    scenes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    sources: Mapped[list[dict[str, str]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    video_object_key: Mapped[str | None] = mapped_column(String(1024))
    youtube_video_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    youtube_url: Mapped[str | None] = mapped_column(String(2048))
    error_message: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    case: Mapped[Case] = relationship()
    creator: Mapped[User] = relationship()
