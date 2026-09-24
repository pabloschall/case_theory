import uuid

from httpx import AsyncClient
from pytest import MonkeyPatch
from sqlalchemy import select

from app.cases import routes as case_routes
from app.cases.models import Case
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id and job_id


async def _register(client: AsyncClient, token: str, suffix: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": f"tier-{suffix}@example.com",
            "username": f"tier_{suffix}",
            "display_name": f"Tier {suffix}",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert response.status_code == 201
    return (await client.get("/api/v1/users/me")).json()


async def _set_plan(user_id: str, plan_code: str, *, verified: bool = True) -> None:
    parsed_user_id = uuid.UUID(user_id)
    async with SessionFactory() as db:
        user = await db.get(User, parsed_user_id)
        plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
        subscription = await db.scalar(
            select(UserSubscription).where(UserSubscription.user_id == parsed_user_id)
        )
        assert user is not None and plan is not None and subscription is not None
        user.is_verified = verified
        subscription.plan_id = plan.id
        await db.commit()


async def test_free_tier_manual_public_cases_are_unlimited_and_ai_is_weekly_limited(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    user = await _register(client, token, "free")
    await _set_plan(str(user["id"]), "free")

    manual = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Manual Free Case",
            "creation_mode": "manual",
            "summary": "Manual public cases do not consume the weekly case allowance.",
            "banner_template": "/case-banners/archive-room.jpg",
        },
    )
    assert manual.status_code == 202
    case_id = manual.json()["id"]

    timeline = await client.post(
        f"/api/v1/cases/{case_id}/timeline",
        headers={"X-CSRF-Token": token},
        json={"occurred_on": "2026-01-01", "title": "Blocked", "description": "Blocked"},
    )
    assert timeline.status_code == 403
    assert (await client.get(f"/api/v1/cases/{case_id}/people")).status_code == 200
    assert (await client.get("/api/v1/messages/conversations")).status_code == 200
    own_notes = await client.get(f"/api/v1/cases/{case_id}/notes")
    assert own_notes.status_code == 200
    assert own_notes.json()["items"] == []
    own_timeline = await client.get(f"/api/v1/cases/{case_id}/my-timeline")
    assert own_timeline.status_code == 200
    assert own_timeline.json() == []
    note = await client.post(
        f"/api/v1/cases/{case_id}/notes",
        headers={"X-CSRF-Token": token},
        json={"title": "Free note", "body": "Free accounts cannot publish this note."},
    )
    assert note.status_code == 403
    personal_timeline = await client.post(
        f"/api/v1/cases/{case_id}/my-timeline",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2026-09-24",
            "title": "Free timeline entry",
            "body": "Free accounts cannot publish this timeline entry.",
        },
    )
    assert personal_timeline.status_code == 403

    second_manual = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Another Manual Public Case",
            "creation_mode": "manual",
            "summary": "This second manual public case is also outside the weekly allowance.",
            "banner_template": "/case-banners/coastal-road.jpg",
        },
    )
    assert second_manual.status_code == 202
    assert (await client.get("/api/v1/users/me")).json()["weekly_cases_remaining"] == 1

    async with SessionFactory() as db:
        item = await db.get(Case, uuid.UUID(case_id))
        assert item is not None
        item.status = "archived"
        await db.commit()

    first_ai = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={"victim_names": "First AI Case", "creation_mode": "ai"},
    )
    assert first_ai.status_code == 202
    assert (await client.get("/api/v1/users/me")).json()["weekly_cases_remaining"] == 0

    exhausted = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={"victim_names": "Second AI Case", "creation_mode": "ai"},
    )
    assert exhausted.status_code == 429
    assert exhausted.json()["error"]["code"] == "weekly_case_limit_reached"
    assert exhausted.json()["error"]["details"]["period"] == "weekly"


async def test_paid_tier_can_create_five_cases_per_utc_week(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    user = await _register(client, token, "investigator")
    await _set_plan(str(user["id"]), "investigator")

    for index in range(5):
        created = await client.post(
            "/api/v1/cases",
            headers={"X-CSRF-Token": token},
            json={"victim_names": f"Investigator AI Case {index}", "creation_mode": "ai"},
        )
        assert created.status_code == 202

    exhausted = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={"victim_names": "Investigator AI Case 6", "creation_mode": "ai"},
    )
    assert exhausted.status_code == 429
    assert exhausted.json()["error"]["code"] == "weekly_case_limit_reached"
    assert exhausted.json()["error"]["details"]["period"] == "weekly"
    assert exhausted.json()["error"]["details"]["limit"] == 5
