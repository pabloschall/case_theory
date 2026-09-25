import pytest
from sqlalchemy import func, select

from app.admin.models import AuditLog
from app.auth.security import hash_password
from app.db.promote_admin import AdminBootstrapError, promote_admin
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


async def create_account(*, verified: bool = True) -> User:
    async with SessionFactory() as db:
        free_plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "free"))
        assert free_plan is not None
        user = User(
            email="owner@example.com",
            username="owner",
            password_hash=hash_password("SecurePassword2026!"),
            is_active=True,
            is_verified=verified,
            profile=UserProfile(display_name="Owner"),
        )
        db.add(user)
        await db.flush()
        db.add(UserSubscription(user_id=user.id, plan_id=free_plan.id))
        await db.commit()
        return user


async def test_promote_admin_is_idempotent() -> None:
    account = await create_account()

    async with SessionFactory() as db:
        await promote_admin(db, " OWNER@example.com ")
        await promote_admin(db, "owner@example.com")

    async with SessionFactory() as db:
        user = await db.get(User, account.id)
        admin_plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "admin"))
        subscriptions = list(
            await db.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == account.id,
                    UserSubscription.is_active.is_(True),
                )
            )
        )
        assert user is not None and user.is_admin
        assert admin_plan is not None
        assert len(subscriptions) == 1
        assert subscriptions[0].plan_id == admin_plan.id
        assert (
            await db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == "user.admin_bootstrapped")
            )
            == 1
        )


async def test_promote_admin_requires_a_verified_account() -> None:
    await create_account(verified=False)

    async with SessionFactory() as db:
        with pytest.raises(AdminBootstrapError, match="Verify the account email"):
            await promote_admin(db, "owner@example.com")
