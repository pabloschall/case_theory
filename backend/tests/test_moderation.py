import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.auth.security import hash_password
from app.cases.models import Case
from app.db.session import SessionFactory
from app.evidence.models import Evidence
from app.moderation.models import ModerationAction, Report
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


async def test_user_report_enters_queue_and_admin_can_lock_pending_review(
    client: AsyncClient,
) -> None:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    registered = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "reporter@example.com",
            "username": "safety_reporter",
            "display_name": "Safety Reporter",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registered.status_code == 201

    async with SessionFactory() as db:
        free_plan = await db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "free")
        )
        assert free_plan
        target = User(
            email="reported@example.com",
            username="reported_user",
            password_hash=hash_password("sourcework123"),
            profile=UserProfile(display_name="Reported User"),
        )
        db.add(target)
        await db.flush()
        db.add(UserSubscription(user_id=target.id, plan_id=free_plan.id))
        await db.commit()
        target_id = target.id

    submitted = await client.post(
        "/api/v1/reports",
        headers={"X-CSRF-Token": token},
        json={
            "resource_type": "user",
            "resource_id": str(target_id),
            "reason_code": "hate_speech",
            "details": "The account posted a racist remark in a case discussion.",
        },
    )
    assert submitted.status_code == 201
    assert submitted.json()["status"] == "pending"
    report_id = submitted.json()["id"]

    duplicate = await client.post(
        "/api/v1/reports",
        headers={"X-CSRF-Token": token},
        json={
            "resource_type": "user",
            "resource_id": str(target_id),
            "reason_code": "harassment",
            "details": "A second report for the same item should be rejected.",
        },
    )
    assert duplicate.status_code == 409

    async with SessionFactory() as db:
        reporter = await db.scalar(select(User).where(User.email == "reporter@example.com"))
        admin_plan = await db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "admin")
        )
        assert reporter and admin_plan
        reporter.is_admin = True
        subscription = await db.scalar(
            select(UserSubscription).where(UserSubscription.user_id == reporter.id)
        )
        assert subscription
        subscription.plan_id = admin_plan.id
        await db.commit()

    queue = await client.get("/api/v1/admin/reports")
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    locked = await client.patch(
        f"/api/v1/admin/reports/{report_id}",
        headers={"X-CSRF-Token": token},
        json={"action": "lock_user", "note": "Locked while context is reviewed."},
    )
    assert locked.status_code == 200

    resolved = await client.patch(
        f"/api/v1/admin/reports/{report_id}",
        headers={"X-CSRF-Token": token},
        json={"action": "resolve", "note": "Violation confirmed."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    async with SessionFactory() as db:
        target = await db.get(User, target_id)
        report = await db.get(Report, uuid.UUID(report_id))
        actions = list(await db.scalars(select(ModerationAction.action)))
        assert target and target.is_active is False
        assert target.moderation_status == "locked_pending_review"
        assert report and report.status == "resolved"
        assert actions == ["lock_user", "resolve"]


async def test_reported_evidence_remains_visible_until_admin_hides_it(
    client: AsyncClient,
) -> None:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    registered = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "evidence-reporter@example.com",
            "username": "evidence_reporter",
            "display_name": "Evidence Reporter",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registered.status_code == 201

    async with SessionFactory() as db:
        reporter = await db.scalar(
            select(User).where(User.email == "evidence-reporter@example.com")
        )
        assert reporter
        case = Case(
            slug="reported-evidence-case",
            title="Reported evidence case",
            victim_names="Fictional Subject",
            status="active",
            privacy="public",
            ai_research_status="complete",
            created_by_user_id=reporter.id,
        )
        db.add(case)
        await db.flush()
        evidence = Evidence(
            case_id=case.id,
            uploaded_by_user_id=reporter.id,
            title="Questionable public source",
            evidence_type="article",
            source_url="https://example.com/source",
            processing_status="available",
            visibility="public",
        )
        db.add(evidence)
        await db.commit()
        case_id = case.id
        evidence_id = evidence.id

    before = await client.get(f"/api/v1/cases/{case_id}/evidence")
    assert before.status_code == 200
    assert before.json()["total"] == 1

    submitted = await client.post(
        "/api/v1/reports",
        headers={"X-CSRF-Token": token},
        json={
            "resource_type": "evidence",
            "resource_id": str(evidence_id),
            "reason_code": "misinformation",
            "details": "The cited page appears fabricated and should be reviewed.",
        },
    )
    assert submitted.status_code == 201
    report_id = submitted.json()["id"]

    still_visible = await client.get(f"/api/v1/cases/{case_id}/evidence")
    assert still_visible.status_code == 200
    assert still_visible.json()["total"] == 1

    async with SessionFactory() as db:
        reporter = await db.scalar(
            select(User).where(User.email == "evidence-reporter@example.com")
        )
        admin_plan = await db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "admin")
        )
        assert reporter and admin_plan
        reporter.is_admin = True
        subscription = await db.scalar(
            select(UserSubscription).where(UserSubscription.user_id == reporter.id)
        )
        assert subscription
        subscription.plan_id = admin_plan.id
        await db.commit()

    hidden = await client.patch(
        f"/api/v1/admin/reports/{report_id}",
        headers={"X-CSRF-Token": token},
        json={"action": "hide", "note": "Hidden while the source is checked."},
    )
    assert hidden.status_code == 200
    hidden_list = await client.get(f"/api/v1/cases/{case_id}/evidence")
    assert hidden_list.status_code == 200
    assert hidden_list.json()["total"] == 0

    restored = await client.patch(
        f"/api/v1/admin/reports/{report_id}",
        headers={"X-CSRF-Token": token},
        json={"action": "restore", "note": "Source was verified."},
    )
    assert restored.status_code == 200
    restored_list = await client.get(f"/api/v1/cases/{case_id}/evidence")
    assert restored_list.status_code == 200
    assert restored_list.json()["total"] == 1
