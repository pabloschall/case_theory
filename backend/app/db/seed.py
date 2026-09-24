import asyncio
from dataclasses import dataclass
from typing import cast

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, verify_password
from app.config.settings import get_settings
from app.db.session import SessionFactory
from app.subscriptions.models import Permission, PlanPermission, SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile

DEMO_PASSWORD = "EillenDemo2026!"


@dataclass(frozen=True)
class DemoUser:
    email: str
    username: str
    display_name: str
    plan_code: str
    is_admin: bool = False


DEMO_USERS = (
    DemoUser("admin@example.com", "eillen_admin", "EILLEN Admin", "admin", is_admin=True),
    DemoUser("free@example.com", "eillen_free", "Free Investigator", "free"),
    DemoUser("paid@example.com", "eillen_paid", "Paid Investigator", "lead"),
)

PERMISSIONS = {
    "case.read_public": "Browse and open public cases",
    "case.create": "Create cases within plan limits",
    "case.create_ai": "Create cases through the AI research pipeline within plan limits",
    "case.follow": "Follow and unfollow public cases",
    "case.import": "Import official public cases as drafts",
    "case.private": "Create and manage private cases",
    "case.edit": "Edit permitted cases",
    "case.invite": "Invite case collaborators",
    "discussion.read": "Read case discussions",
    "discussion.write": "Participate in case discussions",
    "messaging.use": "Send and receive direct messages",
    "research.browse": "Browse official external research sources",
    "evidence.read": "Access case evidence",
    "evidence.upload": "Upload evidence",
    "timeline.read": "Read case timelines",
    "timeline.write": "Suggest timeline events",
    "timeline.approve": "Approve timeline events",
    "map.write": "Add and review case locations",
    "people.read": "View case people and relationships",
    "people.write": "Add people and propose relationships",
    "notes.write": "Create and manage private case notebook notes",
    "ai.research": "Run AI-assisted research",
    "ai.generate_summary": "Generate sourced summaries",
    "ai.generate_timeline": "Generate candidate timeline events",
    "admin.access": "Access administration features",
}

PLAN_DEFINITIONS = {
    "free": {
        "name": "Free",
        "description": "Full investigation access with one new case per week.",
        "tier_level": 1,
        "active_case_limit": -1,
        "weekly_case_limit": 1,
        "monthly_ai_run_limit": -1,
        "storage_bytes_limit": -1,
        "collaborator_limit": -1,
        "daily_ai_case_limit": -1,
        "lifetime_ai_case_limit": -1,
        "permissions": set(PERMISSIONS) - {"admin.access", "notes.write", "timeline.write"},
    },
    "investigator": {
        "name": "Investigator",
        "description": "Full investigation access with five new cases per week.",
        "tier_level": 2,
        "active_case_limit": -1,
        "weekly_case_limit": 5,
        "monthly_ai_run_limit": -1,
        "storage_bytes_limit": -1,
        "collaborator_limit": -1,
        "daily_ai_case_limit": -1,
        "lifetime_ai_case_limit": -1,
        "permissions": set(PERMISSIONS) - {"admin.access"},
    },
    "lead": {
        "name": "Lead Investigator",
        "description": "Full investigation access with five new cases per week.",
        "tier_level": 3,
        "active_case_limit": -1,
        "weekly_case_limit": 5,
        "monthly_ai_run_limit": -1,
        "storage_bytes_limit": -1,
        "collaborator_limit": -1,
        "daily_ai_case_limit": -1,
        "lifetime_ai_case_limit": -1,
        "permissions": set(PERMISSIONS) - {"admin.access"},
    },
    "admin": {
        "name": "Admin",
        "description": "Administrative and moderation access.",
        "tier_level": 0,
        "active_case_limit": 1000,
        "weekly_case_limit": -1,
        "monthly_ai_run_limit": 1000,
        "storage_bytes_limit": 1_000_000_000_000,
        "collaborator_limit": 1000,
        "daily_ai_case_limit": -1,
        "lifetime_ai_case_limit": -1,
        "permissions": set(PERMISSIONS),
    },
}


async def seed() -> None:
    async with SessionFactory() as db:
        permission_by_code: dict[str, Permission] = {}
        plan_by_code: dict[str, SubscriptionPlan] = {}
        for code, description in PERMISSIONS.items():
            permission = await db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, description=description)
                db.add(permission)
                await db.flush()
            permission_by_code[code] = permission
        for code, definition in PLAN_DEFINITIONS.items():
            plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == code))
            fields = {key: value for key, value in definition.items() if key != "permissions"}
            if plan is None:
                plan = SubscriptionPlan(code=code, **fields)
                db.add(plan)
                await db.flush()
            else:
                for key, value in fields.items():
                    setattr(plan, key, value)
            plan_by_code[code] = plan
            current = set(
                (
                    await db.execute(select(PlanPermission.permission_id).where(PlanPermission.plan_id == plan.id))
                ).scalars()
            )
            for permission_code in cast(set[str], definition["permissions"]):
                permission = permission_by_code[permission_code]
                if permission.id not in current:
                    db.add(PlanPermission(plan_id=plan.id, permission_id=permission.id))
            allowed_ids = {
                permission_by_code[code].id
                for code in cast(set[str], definition["permissions"])
            }
            await db.execute(
                delete(PlanPermission).where(
                    PlanPermission.plan_id == plan.id,
                    PlanPermission.permission_id.not_in(allowed_ids),
                )
            )
        if get_settings().environment == "development":
            await seed_demo_users(db, plan_by_code)
        await db.commit()


async def seed_demo_users(
    db: AsyncSession, plan_by_code: dict[str, SubscriptionPlan]
) -> None:
    """Create predictable local accounts without ever seeding them outside development."""
    for definition in DEMO_USERS:
        user = await db.scalar(
            select(User).where(
                or_(User.email == definition.email, User.username == definition.username)
            )
        )
        if user is None:
            user = User(
                email=definition.email,
                username=definition.username,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                is_verified=True,
                is_admin=definition.is_admin,
            )
            db.add(user)
            await db.flush()
            db.add(UserProfile(user_id=user.id, display_name=definition.display_name))
        else:
            user.email = definition.email
            user.username = definition.username
            user.is_active = True
            user.is_verified = True
            user.is_admin = definition.is_admin
            if not verify_password(user.password_hash, DEMO_PASSWORD):
                user.password_hash = hash_password(DEMO_PASSWORD)

            profile = await db.get(UserProfile, user.id)
            if profile is None:
                db.add(UserProfile(user_id=user.id, display_name=definition.display_name))
            else:
                profile.display_name = definition.display_name

        plan = plan_by_code[definition.plan_code]
        subscription = await db.scalar(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user.id,
                UserSubscription.is_active.is_(True),
            )
            .order_by(UserSubscription.starts_at.desc())
        )
        if subscription is None:
            db.add(UserSubscription(user_id=user.id, plan_id=plan.id))
        else:
            subscription.plan_id = plan.id


if __name__ == "__main__":
    asyncio.run(seed())
