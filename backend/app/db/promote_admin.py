import argparse
import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User


class AdminBootstrapError(RuntimeError):
    pass


async def promote_admin(db: AsyncSession, email: str) -> User:
    normalized_email = email.strip().lower()
    user = await db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if user is None:
        raise AdminBootstrapError("No account exists for that email. Register and verify the account first.")
    if not user.is_active or user.deletion_requested_at is not None:
        raise AdminBootstrapError("The account is not active.")
    if not user.is_verified:
        raise AdminBootstrapError("Verify the account email before granting admin access.")

    admin_plan = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == "admin",
            SubscriptionPlan.tier_level == 0,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    if admin_plan is None:
        raise AdminBootstrapError("The admin plan is unavailable. Run the database seed first.")

    subscriptions = list(
        await db.scalars(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user.id,
                UserSubscription.is_active.is_(True),
            )
            .order_by(UserSubscription.starts_at.desc())
        )
    )
    already_configured = user.is_admin and len(subscriptions) == 1 and subscriptions[0].plan_id == admin_plan.id
    if already_configured:
        return user

    before_plan = subscriptions[0].plan_id if subscriptions else None
    if subscriptions:
        subscriptions[0].plan_id = admin_plan.id
        for duplicate in subscriptions[1:]:
            duplicate.is_active = False
    else:
        db.add(UserSubscription(user_id=user.id, plan_id=admin_plan.id))

    was_admin = user.is_admin
    user.is_admin = True
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="user.admin_bootstrapped",
            resource_type="user",
            resource_id=user.id,
            before_snapshot={
                "is_admin": was_admin,
                "plan_id": str(before_plan) if before_plan else None,
            },
            after_snapshot={
                "is_admin": True,
                "plan_id": str(admin_plan.id),
                "plan_code": admin_plan.code,
            },
        )
    )
    await db.commit()
    return user


async def run(email: str) -> None:
    async with SessionFactory() as db:
        user = await promote_admin(db, email)
        print(f"Administrator access is ready for {user.email}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote an existing verified account to the administrator tier.")
    parser.add_argument("email", help="Email address of the registered account")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.email))
    except AdminBootstrapError as exc:
        parser.exit(1, f"Admin bootstrap failed: {exc}\n")


if __name__ == "__main__":
    main()
