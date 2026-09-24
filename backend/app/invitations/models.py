import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base


class CaseInvitation(Base):
    __tablename__ = "case_invitations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(30), default="contributor")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
