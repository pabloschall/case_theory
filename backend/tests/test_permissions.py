from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.subscriptions.permissions import PermissionService
from app.users.models import User, UserProfile


async def test_permissions_follow_the_tier_matrix() -> None:
    async with SessionFactory() as db:
        free = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "free"))
        lead = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "lead"))
        assert free and lead
        free_user = User(
            email="free@example.com",
            username="free_user",
            password_hash=hash_password("somepassword123"),
            profile=UserProfile(display_name="Free User"),
        )
        lead_user = User(
            email="lead@example.com",
            username="lead_user",
            password_hash=hash_password("somepassword123"),
            profile=UserProfile(display_name="Lead User"),
        )
        db.add_all([free_user, lead_user])
        await db.flush()
        db.add_all(
            [
                UserSubscription(user_id=free_user.id, plan_id=free.id),
                UserSubscription(user_id=lead_user.id, plan_id=lead.id),
            ]
        )
        await db.commit()
        service = PermissionService(db)
        assert await service.allows(free_user.id, "case.create")
        assert await service.allows(free_user.id, "case.create_ai")
        assert await service.allows(free_user.id, "case.follow")
        assert await service.allows(free_user.id, "case.import")
        assert await service.allows(free_user.id, "evidence.read")
        assert await service.allows(free_user.id, "ai.research")
        assert await service.allows(free_user.id, "case.private")
        assert not await service.allows(free_user.id, "notes.write")
        assert await service.allows(free_user.id, "timeline.write")
        assert not await service.allows(free_user.id, "timeline.private_write")
        assert not await service.allows(free_user.id, "admin.access")
        assert await service.allows(lead_user.id, "case.create")
        assert await service.allows(lead_user.id, "case.import")
        assert await service.allows(lead_user.id, "ai.research")
        assert await service.allows(lead_user.id, "case.private")
        assert await service.allows(lead_user.id, "notes.write")
        assert await service.allows(lead_user.id, "timeline.write")
        assert await service.allows(lead_user.id, "timeline.private_write")
