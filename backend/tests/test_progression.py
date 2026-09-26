import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.cases.models import Case
from app.db.session import SessionFactory
from app.progression.models import ProgressionLedgerEntry, UserBadge
from app.progression.service import ProgressionEvent, ProgressionService
from app.users.models import User


async def _register(client: AsyncClient) -> str:
    csrf = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    response = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": csrf},
        json={
            "email": "progress@example.com",
            "username": "progress_user",
            "display_name": "Progress User",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert response.status_code == 201
    return csrf


async def test_progression_awards_once_and_reveals_badge(client: AsyncClient) -> None:
    csrf = await _register(client)
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "progress@example.com"))
        assert user is not None
        evidence_id = uuid.uuid4()
        event = ProgressionEvent(
            user_id=user.id,
            event_key=f"external_evidence_added:{evidence_id}",
            rule_code="external_evidence_added",
            resource_type="evidence",
            resource_id=str(evidence_id),
        )
        await ProgressionService(db).award_safely(event)
        await ProgressionService(db).award_safely(event)

    summary = await client.get("/api/v1/users/me/progression")
    assert summary.status_code == 200
    body = summary.json()
    assert body["lifetime_xp"] == 10
    assert body["rank"]["code"] == "observer"
    assert [badge["code"] for badge in body["pending_badges"]] == ["first_citation"]
    assert len(body["pending_receipts"]) == 1

    acknowledged = await client.patch(
        "/api/v1/users/me/progression/acknowledge",
        headers={"X-CSRF-Token": csrf},
        json={
            "badge_codes": ["first_citation"],
            "receipt_ids": [body["pending_receipts"][0]["id"]],
        },
    )
    assert acknowledged.status_code == 204
    refreshed = (await client.get("/api/v1/users/me/progression")).json()
    assert refreshed["pending_badges"] == []
    assert refreshed["pending_receipts"] == []

    async with SessionFactory() as db:
        assert len(list(await db.scalars(select(ProgressionLedgerEntry)))) == 1
        assert len(list(await db.scalars(select(UserBadge)))) == 1


async def test_daily_cap_limits_xp_but_keeps_events_idempotent(client: AsyncClient) -> None:
    await _register(client)
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "progress@example.com"))
        assert user is not None
        service = ProgressionService(db)
        for index in range(5):
            await service.award_safely(
                ProgressionEvent(
                    user_id=user.id,
                    event_key=f"external_evidence_added:{index}",
                    rule_code="external_evidence_added",
                )
            )
    body = (await client.get("/api/v1/users/me/progression")).json()
    assert body["lifetime_xp"] == 30
    ledger = (await client.get("/api/v1/users/me/progression/ledger")).json()
    assert ledger["total"] == 3


async def test_case_created_awards_badge_without_xp(client: AsyncClient) -> None:
    await _register(client)
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "progress@example.com"))
        assert user is not None
        service = ProgressionService(db)
        await service.award_safely(
            ProgressionEvent(
                user_id=user.id,
                event_key=f"case_created:{uuid.uuid4()}",
                rule_code="case_created",
                resource_type="case",
            )
        )

    body = (await client.get("/api/v1/users/me/progression")).json()
    assert body["lifetime_xp"] == 0
    assert [badge["code"] for badge in body["pending_badges"]] == ["case_file_opened"]
    assert body["pending_receipts"] == []


async def test_source_scout_requires_ten_sources_across_three_cases(client: AsyncClient) -> None:
    await _register(client)
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "progress@example.com"))
        assert user is not None
        cases = [
            Case(
                slug=f"progress-case-{index}",
                title=f"Progress Case {index}",
                victim_names=f"Person {index}",
                privacy="public",
                ai_research_status="complete",
                created_by_user_id=user.id,
            )
            for index in range(3)
        ]
        db.add_all(cases)
        await db.commit()
        service = ProgressionService(db)
        for index in range(10):
            await service.award_safely(
                ProgressionEvent(
                    user_id=user.id,
                    event_key=f"external_evidence_added:scout-{index}",
                    rule_code="external_evidence_added",
                    resource_type="evidence",
                    resource_id=f"scout-{index}",
                    case_id=cases[index % 3].id,
                )
            )

    body = (await client.get("/api/v1/users/me/progression")).json()
    earned_codes = {badge["code"] for badge in body["badges"] if badge["earned_at"]}
    assert "first_citation" in earned_codes
    assert "source_scout" in earned_codes
    assert body["lifetime_xp"] == 30


async def test_linking_evidence_to_person_awards_first_connection(client: AsyncClient) -> None:
    await _register(client)
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "progress@example.com"))
        assert user is not None
        await ProgressionService(db).award_safely(
            ProgressionEvent(
                user_id=user.id,
                event_key=f"evidence_person_linked:{uuid.uuid4()}:{uuid.uuid4()}",
                rule_code="evidence_person_linked",
                resource_type="evidence_person_link",
            )
        )

    body = (await client.get("/api/v1/users/me/progression")).json()
    assert body["lifetime_xp"] == 4
    assert [badge["code"] for badge in body["pending_badges"]] == ["first_connection"]
