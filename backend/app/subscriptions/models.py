import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.db.base import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(500), default="")
    tier_level: Mapped[int] = mapped_column(Integer, default=1)
    active_case_limit: Mapped[int] = mapped_column(Integer, default=0)
    weekly_case_limit: Mapped[int] = mapped_column(Integer, default=1)
    monthly_ai_run_limit: Mapped[int] = mapped_column(Integer, default=0)
    storage_bytes_limit: Mapped[int] = mapped_column(BigInteger, default=0)
    collaborator_limit: Mapped[int] = mapped_column(Integer, default=0)
    daily_ai_case_limit: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_ai_case_limit: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    permissions: Mapped[list["PlanPermission"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255))


class PlanPermission(Base):
    __tablename__ = "plan_permissions"
    __table_args__ = (UniqueConstraint("plan_id", "permission_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscription_plans.id", ondelete="CASCADE"))
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"))
    plan: Mapped[SubscriptionPlan] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscription_plans.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[SubscriptionPlan] = relationship()


class AIUsageRecord(Base):
    __tablename__ = "ai_usage_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"), unique=True, index=True, nullable=True
    )
    usage_type: Mapped[str] = mapped_column(String(50), default="case_creation", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
