import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.admin.models import AuditLog
from app.auth.security import hash_password
from app.cases.models import Case
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


async def test_admin_can_search_users_change_tiers_and_delete_cases(
    client: AsyncClient,
) -> None:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    registered = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "admin-workspace@example.com",
            "username": "admin_workspace",
            "display_name": "Workspace Admin",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registered.status_code == 201

    async with SessionFactory() as db:
        admin = await db.scalar(select(User).where(User.email == "admin-workspace@example.com"))
        admin_plan = await db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "admin")
        )
        free_plan = await db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "free")
        )
        assert admin and admin_plan and free_plan
        admin.is_admin = True
        admin_subscription = await db.scalar(
            select(UserSubscription).where(UserSubscription.user_id == admin.id)
        )
        assert admin_subscription
        admin_subscription.plan_id = admin_plan.id
        target = User(
            email="case-owner@example.com",
            username="case_owner",
            password_hash=hash_password("sourcework123"),
            profile=UserProfile(display_name="Case Owner"),
        )
        db.add(target)
        await db.flush()
        db.add(UserSubscription(user_id=target.id, plan_id=free_plan.id))
        case = Case(
            slug="admin-search-case",
            title="Admin Search Case",
            victim_names="Admin Search Case",
            status="active",
            privacy="public",
            ai_research_status="complete",
            created_by_user_id=target.id,
        )
        db.add(case)
        await db.commit()
        admin_id = admin.id
        target_id = target.id
        case_id = case.id

    users = await client.get("/api/v1/admin/users", params={"q": "case-owner@"})
    assert users.status_code == 200
    assert users.json()["total"] == 1
    assert users.json()["items"][0]["id"] == str(target_id)
    assert users.json()["items"][0]["tier_level"] == 1

    created_admin = await client.post(
        "/api/v1/admin/users",
        headers={"X-CSRF-Token": token},
        json={
            "email": "second-admin@example.com",
            "username": "second_admin",
            "display_name": "Second Admin",
            "password": "secure-admin-123",
        },
    )
    assert created_admin.status_code == 201
    assert created_admin.json()["tier_level"] == 0
    assert created_admin.json()["is_admin"] is True
    created_admin_id = created_admin.json()["id"]

    duplicate_admin = await client.post(
        "/api/v1/admin/users",
        headers={"X-CSRF-Token": token},
        json={
            "email": "second-admin@example.com",
            "username": "another_admin",
            "display_name": "Duplicate Admin",
            "password": "secure-admin-123",
        },
    )
    assert duplicate_admin.status_code == 409

    self_delete = await client.delete(
        f"/api/v1/admin/users/{admin_id}", headers={"X-CSRF-Token": token}
    )
    assert self_delete.status_code == 409

    deleted_admin = await client.delete(
        f"/api/v1/admin/users/{created_admin_id}", headers={"X-CSRF-Token": token}
    )
    assert deleted_admin.status_code == 200
    deleted_search = await client.get(
        "/api/v1/admin/users", params={"q": "second-admin@example.com"}
    )
    assert deleted_search.status_code == 200
    assert deleted_search.json()["total"] == 0

    changed = await client.patch(
        f"/api/v1/admin/users/{target_id}/tier",
        headers={"X-CSRF-Token": token},
        json={"tier_level": 3},
    )
    assert changed.status_code == 200
    assert changed.json()["tier_level"] == 3
    assert changed.json()["plan_code"] == "lead"

    self_change = await client.patch(
        f"/api/v1/admin/users/{admin_id}/tier",
        headers={"X-CSRF-Token": token},
        json={"tier_level": 1},
    )
    assert self_change.status_code == 409

    cases = await client.get("/api/v1/admin/cases", params={"q": "case-owner@"})
    assert cases.status_code == 200
    assert cases.json()["total"] == 1
    assert cases.json()["items"][0]["owner_email"] == "case-owner@example.com"

    deleted = await client.delete(
        f"/api/v1/admin/cases/{case_id}", headers={"X-CSRF-Token": token}
    )
    assert deleted.status_code == 200

    async with SessionFactory() as db:
        assert await db.get(Case, case_id) is None
        actions = set(await db.scalars(select(AuditLog.action)))
        deleted_user = await db.get(User, uuid.UUID(created_admin_id))
        assert deleted_user is not None
        assert deleted_user.is_active is False
        assert deleted_user.deletion_requested_at is not None
        assert deleted_user.email.endswith("@deleted.invalid")
        assert actions == {
            "user.admin_created",
            "user.deleted",
            "user.tier_changed",
            "case.deleted",
        }
