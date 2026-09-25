import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base
from app.users.models import User


class DirectConversation(Base):
    __tablename__ = "direct_conversations"
    __table_args__ = (
        UniqueConstraint("user_one_id", "user_two_id"),
        Index(
            "ix_direct_conversations_user_one_updated_id",
            "user_one_id",
            "updated_at",
            "id",
        ),
        Index(
            "ix_direct_conversations_user_two_updated_id",
            "user_two_id",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_one_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    user_two_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    user_one_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_two_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_one: Mapped[User] = relationship(foreign_keys=[user_one_id])
    user_two: Mapped[User] = relationship(foreign_keys=[user_two_id])
    messages: Mapped[list["DirectMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class DirectMessage(Base):
    __tablename__ = "direct_messages"
    __table_args__ = (
        Index(
            "ix_direct_messages_conversation_created_id",
            "conversation_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("direct_conversations.id", ondelete="CASCADE"), index=True
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )

    conversation: Mapped[DirectConversation] = relationship(back_populates="messages")
    sender: Mapped[User] = relationship()
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("direct_conversations.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("direct_messages.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    storage_object_key: Mapped[str] = mapped_column(String(1024), unique=True)
    original_filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(150))
    file_size: Mapped[int] = mapped_column(BigInteger)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    message: Mapped[DirectMessage | None] = relationship(back_populates="attachments")
