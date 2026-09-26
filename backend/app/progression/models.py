import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base


class ProgressionRank(Base):
    __tablename__ = "progression_ranks"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    threshold: Mapped[int] = mapped_column(Integer, unique=True)
    rank_order: Mapped[int] = mapped_column(Integer, unique=True)
    icon_key: Mapped[str] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ProgressionRule(Base):
    __tablename__ = "progression_rules"

    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    reason: Mapped[str] = mapped_column(String(160))
    xp: Mapped[int] = mapped_column(Integer)
    daily_cap: Mapped[int | None] = mapped_column(Integer)
    lifetime_once: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ProgressionProfile(Base):
    __tablename__ = "progression_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lifetime_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    highest_rank_code: Mapped[str] = mapped_column(
        ForeignKey("progression_ranks.code"), default="observer", server_default="observer"
    )
    show_rank: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    show_badges: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ProgressionLedgerEntry(Base):
    __tablename__ = "progression_ledger"
    __table_args__ = (Index("ix_progression_ledger_user_created", "user_id", "created_at", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_key: Mapped[str] = mapped_column(String(180), unique=True)
    rule_code: Mapped[str] = mapped_column(ForeignKey("progression_rules.code"), index=True)
    xp_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(160))
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    is_shadow: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    displayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BadgeDefinition(Base):
    __tablename__ = "badge_definitions"

    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    criteria: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    icon_key: Mapped[str] = mapped_column(String(40))
    criteria_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    badge_code: Mapped[str] = mapped_column(ForeignKey("badge_definitions.code", ondelete="RESTRICT"), index=True)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
