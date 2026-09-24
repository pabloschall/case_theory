import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.subscriptions.models import AIUsageRecord, Permission, PlanPermission, UserSubscription
from app.users.models import User


@dataclass(frozen=True)
class PermissionContext:
    plan_code: str
    tier_level: int
    active_case_limit: int
    weekly_case_limit: int
    permissions: frozenset[str]


@dataclass(frozen=True)
class AIAllowance:
    remaining: int | None
    period: str
    resets_at: datetime | None


class PermissionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_user(self, user_id: uuid.UUID, *, is_admin: bool = False) -> PermissionContext:
        subscription = await self._subscription(user_id)
        permissions: frozenset[str] = frozenset()
        if subscription is not None:
            permissions_result = await self.db.execute(
                select(Permission.code)
                .join(PlanPermission, PlanPermission.permission_id == Permission.id)
                .where(PlanPermission.plan_id == subscription.plan_id)
            )
            permissions = frozenset(permissions_result.scalars())
        if is_admin:
            permissions = frozenset((await self.db.scalars(select(Permission.code))).all())
            return PermissionContext("admin", 0, -1, -1, permissions | {"admin.access"})
        return PermissionContext(
            subscription.plan.code if subscription else "free",
            subscription.plan.tier_level if subscription else 1,
            subscription.plan.active_case_limit if subscription else 0,
            subscription.plan.weekly_case_limit if subscription else 0,
            permissions,
        )

    async def allows(self, user_id: uuid.UUID, permission: str, *, is_admin: bool = False) -> bool:
        context = await self.for_user(user_id, is_admin=is_admin)
        return is_admin or permission in context.permissions

    async def require(
        self,
        user: User,
        permission: str,
        *,
        required_tier: int = 2,
        message: str = "Upgrade your plan to use this feature",
    ) -> None:
        if not await self.allows(user.id, permission, is_admin=user.is_admin):
            raise AppError(
                403,
                "upgrade_required",
                message,
                {"permission": permission, "required_tier": required_tier},
            )

    async def case_allowance(self, user: User) -> AIAllowance:
        if user.is_admin:
            return AIAllowance(None, "weekly", None)
        subscription = await self._subscription(user.id)
        if subscription is None:
            return AIAllowance(0, "weekly", None)
        start, reset = _utc_week_window()
        from app.cases.models import Case

        used = int(
            await self.db.scalar(
                select(func.count(Case.id)).where(
                    Case.created_by_user_id == user.id,
                    Case.created_at >= start,
                    Case.counts_toward_weekly_limit.is_(True),
                )
            )
            or 0
        )
        return AIAllowance(max(0, subscription.plan.weekly_case_limit - used), "weekly", reset)

    async def require_case_creation(self, user: User, *, enforce_limit: bool = True) -> None:
        subscription = await self.db.scalar(
            select(UserSubscription)
            .where(UserSubscription.user_id == user.id, UserSubscription.is_active.is_(True))
            .options(selectinload(UserSubscription.plan))
            .order_by(UserSubscription.starts_at.desc())
            .limit(1)
            .with_for_update()
        )
        if not user.is_admin and subscription is None:
            raise AppError(403, "subscription_required", "An active account plan is required")
        if not user.is_admin and subscription is not None:
            if not user.is_verified:
                raise AppError(
                    403,
                    "email_verification_required",
                    "Verify your email before creating a case",
                )
            if not enforce_limit:
                return
            allowance = await self.case_allowance(user)
            if allowance.remaining == 0:
                raise AppError(
                    429,
                    "weekly_case_limit_reached",
                    "Your weekly case creation limit has been reached",
                    {
                        "period": allowance.period,
                        "limit": subscription.plan.weekly_case_limit,
                        "resets_at": allowance.resets_at.isoformat() if allowance.resets_at else None,
                    },
                )

    def record_ai_case(self, user: User, case_id: uuid.UUID) -> None:
        self.db.add(AIUsageRecord(user_id=user.id, case_id=case_id))

    async def _subscription(self, user_id: uuid.UUID) -> UserSubscription | None:
        result = await self.db.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id, UserSubscription.is_active.is_(True))
            .options(selectinload(UserSubscription.plan))
            .order_by(UserSubscription.starts_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _usage_count(self, user_id: uuid.UUID, *, since: datetime | None = None) -> int:
        statement = select(func.count(AIUsageRecord.id)).where(
            AIUsageRecord.user_id == user_id,
            AIUsageRecord.usage_type == "case_creation",
        )
        if since is not None:
            statement = statement.where(AIUsageRecord.created_at >= since)
        return int(await self.db.scalar(statement) or 0)


def _utc_week_window() -> tuple[datetime, datetime]:
    now = utc_now()
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
    start = start_of_day - timedelta(days=now.weekday())
    return start, start + timedelta(days=7)
