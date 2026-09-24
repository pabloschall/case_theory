from httpx import AsyncClient
from sqlalchemy import func, select

from app.auth.security import verify_password
from app.db.seed import DEMO_PASSWORD, DEMO_USERS, seed_demo_users
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


async def test_demo_users_are_seeded_idempotently_with_expected_access() -> None:
    async with SessionFactory() as db:
        plans = {
            plan.code: plan for plan in (await db.scalars(select(SubscriptionPlan))).all()
        }

        await seed_demo_users(db, plans)
        await db.commit()
        await seed_demo_users(db, plans)
        await db.commit()

        emails = [definition.email for definition in DEMO_USERS]
        assert await db.scalar(
            select(func.count()).select_from(User).where(User.email.in_(emails))
        ) == len(DEMO_USERS)

        for definition in DEMO_USERS:
            user = await db.scalar(select(User).where(User.email == definition.email))
            assert user is not None
            assert user.username == definition.username
            assert user.is_active
            assert user.is_verified
            assert user.is_admin is definition.is_admin
            assert verify_password(user.password_hash, DEMO_PASSWORD)

            profile = await db.get(UserProfile, user.id)
            assert profile is not None
            assert profile.display_name == definition.display_name

            subscriptions = (
                await db.scalars(
                    select(UserSubscription).where(
                        UserSubscription.user_id == user.id,
                        UserSubscription.is_active.is_(True),
                    )
                )
            ).all()
            assert len(subscriptions) == 1
            assert subscriptions[0].plan_id == plans[definition.plan_code].id


async def test_demo_users_can_log_in_through_the_api(client: AsyncClient) -> None:
    async with SessionFactory() as db:
        plans = {
            plan.code: plan for plan in (await db.scalars(select(SubscriptionPlan))).all()
        }
        await seed_demo_users(db, plans)
        await db.commit()

    csrf_response = await client.get("/api/v1/auth/csrf")
    csrf_token = csrf_response.json()["csrf_token"]

    for definition in DEMO_USERS:
        response = await client.post(
            "/api/v1/auth/login",
            headers={"X-CSRF-Token": csrf_token},
            json={"email": definition.email, "password": DEMO_PASSWORD},
        )
        assert response.status_code == 200

        current_user = await client.get("/api/v1/users/me")
        assert current_user.status_code == 200
        assert current_user.json()["email"] == definition.email
        assert current_user.json()["plan_code"] == definition.plan_code
        assert ("admin.access" in current_user.json()["permissions"]) is definition.is_admin
