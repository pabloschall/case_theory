import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test-eillen.db"
os.environ["SECRET_KEY"] = "test-secret-key-with-more-than-32-characters"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.service import AuthService
from app.db.base import Base
from app.db.seed import PERMISSIONS, PLAN_DEFINITIONS
from app.db.session import SessionFactory, engine
from app.main import app
from app.progression.definitions import BADGE_DEFINITIONS, RANK_DEFINITIONS, RULE_DEFINITIONS
from app.progression.models import BadgeDefinition, ProgressionRank, ProgressionRule
from app.subscriptions.models import Permission, PlanPermission, SubscriptionPlan, UserSubscription


@pytest.fixture(autouse=True)
async def database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with SessionFactory() as db:
        permissions: dict[str, Permission] = {}
        for code, description in PERMISSIONS.items():
            item = Permission(code=code, description=description)
            db.add(item)
            permissions[code] = item
        await db.flush()
        for code, definition in PLAN_DEFINITIONS.items():
            fields = {key: value for key, value in definition.items() if key != "permissions"}
            plan = SubscriptionPlan(code=code, **fields)
            db.add(plan)
            await db.flush()
            for permission_code in definition["permissions"]:
                db.add(PlanPermission(plan_id=plan.id, permission_id=permissions[permission_code].id))
        db.add_all(
            [
                ProgressionRank(
                    code=code,
                    name=name,
                    threshold=threshold,
                    rank_order=rank_order,
                    icon_key=icon_key,
                )
                for code, name, threshold, rank_order, icon_key in RANK_DEFINITIONS
            ]
        )
        db.add_all(
            [
                ProgressionRule(
                    code=code,
                    reason=reason,
                    xp=xp,
                    daily_cap=daily_cap,
                    lifetime_once=lifetime_once,
                )
                for code, reason, xp, daily_cap, lifetime_once in RULE_DEFINITIONS
            ]
        )
        db.add_all(
            [
                BadgeDefinition(
                    code=code,
                    name=name,
                    description=description,
                    criteria=criteria,
                    category="research_craft",
                    icon_key=icon_key,
                    sort_order=sort_order,
                )
                for code, name, description, criteria, icon_key, sort_order in BADGE_DEFINITIONS
            ]
        )
        await db.commit()
    yield


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as value:
        yield value


@pytest.fixture
def paid_signups(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep feature tests focused by registering their users on the Lead plan."""
    original = AuthService.register

    async def register_as_paid(self: AuthService, *args: object, **kwargs: object):
        user = await original(self, *args, **kwargs)
        plan = await self.db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "lead"))
        subscription = await self.db.scalar(select(UserSubscription).where(UserSubscription.user_id == user.id))
        assert plan is not None and subscription is not None
        subscription.plan_id = plan.id
        user.is_verified = True
        await self.db.commit()
        return user

    monkeypatch.setattr(AuthService, "register", register_as_paid)
