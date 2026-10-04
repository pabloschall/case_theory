import uuid
from xml.etree import ElementTree

import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch
from sqlalchemy import select

from app.cases import routes
from app.cases.models import Case, Source, TimelineEvent, TimelineEventSource
from app.config.settings import get_settings
from app.db.session import SessionFactory
from app.users.models import User


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


@pytest.mark.usefixtures("paid_signups")
async def test_create_search_and_open_case(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "generate_case", StubTask())
    csrf_response = await client.get("/api/v1/auth/csrf")
    token = csrf_response.json()["csrf_token"]
    registered = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "case-owner@example.com",
            "username": "case_owner",
            "display_name": "Case Owner",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registered.status_code == 201
    created = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Morgan Vale",
            "year": 1998,
            "location": "Northpoint, Oregon",
            "additional_context": "Last publicly reported near a trailhead.",
        },
    )
    assert created.status_code == 202
    case = created.json()
    assert case["victim_names"] == "Morgan Vale"
    assert case["ai_research_status"] == "queued"
    progression = (await client.get("/api/v1/users/me/progression")).json()
    assert "case_file_opened" in {
        badge["code"] for badge in progression["pending_badges"]
    }

    following = await client.get("/api/v1/cases/following")
    assert following.status_code == 200
    assert following.json() == []

    search = await client.get("/api/v1/cases?q=Northpoint")
    assert search.status_code == 200
    assert search.json()["items"][0]["id"] == case["id"]
    assert search.json()["items"][0]["discussion_count"] == 0
    assert search.json()["items"][0]["created_at"]
    assert search.json()["page"] == 1
    assert search.json()["page_size"] == 12
    assert search.json()["total"] == 1
    assert search.json()["has_next"] is False

    sitemap_response = await client.get("/sitemap.xml")
    assert sitemap_response.status_code == 200
    assert sitemap_response.headers["content-type"].startswith("application/xml")
    sitemap = ElementTree.fromstring(sitemap_response.content)
    locations = {
        node.text for node in sitemap.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    }
    assert f"{get_settings().public_site_url}/cases" in locations
    assert f"{get_settings().public_site_url}/cases/{case['id']}" in locations

    year_search = await client.get("/api/v1/cases?q=1998")
    assert year_search.status_code == 200
    assert year_search.json()["items"][0]["id"] == case["id"]

    active_case = (
        await client.post(
            "/api/v1/cases",
            headers={"X-CSRF-Token": token},
            json={"victim_names": "Harbor Ledger", "location": "Port Alder"},
        )
    ).json()
    thread = await client.post(
        f"/api/v1/cases/{active_case['id']}/discussions",
        headers={"X-CSRF-Token": token},
        json={
            "title": "Compare the harbor records",
            "body": "Which public logs support the reported arrival time?",
            "thread_type": "question",
        },
    )
    assert thread.status_code == 201
    commented = await client.post(
        f"/api/v1/cases/{active_case['id']}/discussions/{thread.json()['id']}/comments",
        headers={"X-CSRF-Token": token},
        json={"body": "The published manifest gives one independently sourced time."},
    )
    assert commented.status_code == 201

    assert (await client.get(f"/api/v1/cases/{case['id']}")).json()["view_count"] == 0
    first_view = await client.post(f"/api/v1/cases/{case['id']}/view", headers={"X-CSRF-Token": token})
    assert first_view.status_code == 200
    assert first_view.json() == {"view_count": 1}
    second_view = await client.post(f"/api/v1/cases/{case['id']}/view", headers={"X-CSRF-Token": token})
    assert second_view.json() == {"view_count": 2}
    assert (await client.get(f"/api/v1/cases/{case['id']}")).json()["view_count"] == 2
    most_viewed = await client.get("/api/v1/cases?sort=views")
    assert most_viewed.status_code == 200
    assert most_viewed.json()["items"][0]["id"] == case["id"]
    assert most_viewed.json()["items"][0]["view_count"] == 2

    popular = await client.get("/api/v1/cases?sort=popular")
    assert popular.status_code == 200
    assert popular.json()["items"][0]["id"] == active_case["id"]
    assert popular.json()["items"][0]["discussion_count"] == 2

    first_page = await client.get("/api/v1/cases?page=1&page_size=1")
    second_page = await client.get("/api/v1/cases?page=2&page_size=1")
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert first_page.json()["total_pages"] == 2
    assert first_page.json()["has_next"] is True
    assert first_page.json()["has_previous"] is False
    assert second_page.json()["has_next"] is False
    assert second_page.json()["has_previous"] is True
    assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    for section in ("evidence", "discussions", "locations", "people"):
        public_section = await client.get(f"/api/v1/cases/{active_case['id']}/{section}")
        assert public_section.status_code == 200

    invalid_sort = await client.get("/api/v1/cases?sort=unknown")
    assert invalid_sort.status_code == 422

    opened = await client.get(f"/api/v1/cases/{case['id']}")
    assert opened.status_code == 200
    assert opened.json()["timeline"] == []
    assert opened.json()["is_following"] is False

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    guest_search = await client.get("/api/v1/cases?q=Morgan")
    assert guest_search.status_code == 200
    assert guest_search.json()["items"][0]["id"] == case["id"]
    assert guest_search.json()["items"][0]["is_owner"] is False
    assert guest_search.json()["items"][0]["is_following"] is False
    guest_case = await client.get(f"/api/v1/cases/{case['id']}")
    assert guest_case.status_code == 200
    assert guest_case.json()["is_owner"] is False


@pytest.mark.usefixtures("paid_signups")
async def test_following_is_explicit_and_separate_from_ownership(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "follow-owner@example.com",
            "username": "follow_owner",
            "display_name": "Follow Owner",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    case = (
        await client.post(
            "/api/v1/cases",
            headers={"X-CSRF-Token": token},
            json={"victim_names": "Fictional Follow Case"},
        )
    ).json()

    assert (await client.get("/api/v1/cases/mine")).json()[0]["id"] == case["id"]
    assert (await client.get("/api/v1/cases/following")).json() == []
    owner_follow = await client.post(
        f"/api/v1/cases/{case['id']}/follow",
        headers={"X-CSRF-Token": token},
    )
    assert owner_follow.status_code == 409
    assert owner_follow.json()["error"]["code"] == "owner_cannot_follow"

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "case-follower@example.com",
            "username": "case_follower",
            "display_name": "Case Follower",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )

    before_follow = await client.get(f"/api/v1/cases/{case['id']}")
    assert before_follow.json()["is_following"] is False
    followed = await client.post(
        f"/api/v1/cases/{case['id']}/follow",
        headers={"X-CSRF-Token": token},
    )
    assert followed.status_code == 200
    assert followed.json() == {"is_following": True}
    following = await client.get("/api/v1/cases/following")
    assert [item["id"] for item in following.json()] == [case["id"]]
    assert (await client.get(f"/api/v1/cases/{case['id']}")).json()["is_following"] is True

    unfollowed = await client.delete(
        f"/api/v1/cases/{case['id']}/follow",
        headers={"X-CSRF-Token": token},
    )
    assert unfollowed.status_code == 200
    assert unfollowed.json() == {"is_following": False}
    assert (await client.get("/api/v1/cases/following")).json() == []


@pytest.mark.usefixtures("paid_signups")
async def test_create_case_without_year_or_location(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "generate_case", StubTask())
    csrf_response = await client.get("/api/v1/auth/csrf")
    token = csrf_response.json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "minimal-case@example.com",
            "username": "minimal_case",
            "display_name": "Minimal Case Owner",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )

    created = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={"victim_names": "Avery Stone"},
    )

    assert created.status_code == 202
    case = created.json()
    assert case["title"] == "Avery Stone"
    assert case["year"] is None
    assert case["location"] is None

    async with SessionFactory() as db:
        case_id = uuid.UUID(case["id"])
        stored_case = await db.get(Case, case_id)
        assert stored_case
        stored_case.cover_image_object_key = f"cases/{case_id}/covers/generated.webp"
        stored_case.cover_image_url = f"/api/v1/cases/{case_id}/cover"
        source = Source(
            case_id=case_id,
            url="https://example.gov/case",
            canonical_url="https://example.gov/case",
            title="Official case page",
            position=1,
            publisher="example.gov",
            source_type="government",
            reliability_metadata={"classification_basis": "publisher provenance"},
        )
        event = TimelineEvent(
            case_id=case_id,
            date_label="Date unknown",
            title="Candidate event",
            description="A sourced candidate event.",
        )
        db.add_all([source, event])
        await db.flush()
        db.add(TimelineEventSource(timeline_event_id=event.id, source_id=source.id))
        await db.commit()

    opened = await client.get(f"/api/v1/cases/{case['id']}")
    assert opened.status_code == 200
    assert opened.json()["sources"][0]["url"] == "https://example.gov/case"
    assert opened.json()["timeline"][0]["sources"][0]["title"] == "Official case page"
    cover = await client.get(f"/api/v1/cases/{case['id']}/cover", follow_redirects=False)
    assert cover.status_code == 307
    assert f"cases%2F{case['id']}%2Fcovers%2Fgenerated.webp" in cover.headers["location"]

    async with SessionFactory() as db:
        admin_user = await db.scalar(select(User).where(User.username == "minimal_case"))
        assert admin_user
        admin_user.is_admin = True
        await db.commit()

    admin_list = await client.get("/api/v1/admin/cases")
    assert admin_list.status_code == 200
    assert admin_list.json()["items"][0]["id"] == case["id"]

    deleted = await client.delete(
        f"/api/v1/admin/cases/{case['id']}",
        headers={"X-CSRF-Token": token},
    )
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/cases/{case['id']}")
    assert missing.status_code == 404


@pytest.mark.usefixtures("paid_signups")
async def test_create_manual_case_with_summary_and_banner(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    class UnexpectedTask:
        def delay(self, case_id: str, job_id: str) -> None:
            raise AssertionError(f"Manual case queued AI generation: {case_id} {job_id}")

    monkeypatch.setattr(routes, "generate_case", UnexpectedTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "manual-case@example.com",
            "username": "manual_case",
            "display_name": "Manual Case Owner",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )

    created = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "The Northpoint Files",
            "creation_mode": "manual",
            "summary": "An investigator-authored overview that remains separate from AI research.",
            "banner_template": "/case-banners/archive-room.jpg",
        },
    )

    assert created.status_code == 202
    case = created.json()
    assert case["ai_research_status"] == "complete"
    assert case["cover_image_url"] == "/case-banners/archive-room.jpg"
    assert case["summary"] == {
        "body": "An investigator-authored overview that remains separate from AI research.",
        "source": "user",
        "ai_model": None,
    }

    invalid = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Invalid Manual Case",
            "creation_mode": "manual",
            "summary": "Too short",
            "banner_template": "/case-banners/archive-room.jpg",
        },
    )
    assert invalid.status_code == 422


@pytest.mark.usefixtures("paid_signups")
async def test_only_admin_can_research_an_existing_case(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "case-research@example.com",
            "username": "case_research_admin",
            "display_name": "Case Research Admin",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    current_user = (await client.get("/api/v1/users/me")).json()
    case = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Manual Research Case",
            "creation_mode": "manual",
            "summary": "A manual overview that an administrator may later research again.",
            "banner_template": "/case-banners/archive-room.jpg",
        },
    )
    case_id = case.json()["id"]

    forbidden = await client.post(
        f"/api/v1/cases/{case_id}/research",
        headers={"X-CSRF-Token": token},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "admin_required"

    async with SessionFactory() as db:
        user = await db.get(User, uuid.UUID(current_user["id"]))
        assert user is not None
        user.is_admin = True
        await db.commit()

    queued = await client.post(
        f"/api/v1/cases/{case_id}/research",
        headers={"X-CSRF-Token": token},
    )
    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"


@pytest.mark.usefixtures("paid_signups")
async def test_user_can_add_unverified_timeline_event(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "timeline-author@example.com",
            "username": "timeline_author",
            "display_name": "Timeline Author",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    case_id = (
        await client.post(
            "/api/v1/cases",
            headers={"X-CSRF-Token": token},
            json={"victim_names": "Fictional Timeline Case"},
        )
    ).json()["id"]

    created = await client.post(
        f"/api/v1/cases/{case_id}/timeline",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2004-08-20",
            "occurred_time": "18:30",
            "title": "Journal entry recorded",
            "description": "A user-added event requiring source review.",
        },
    )

    assert created.status_code == 201
    assert created.json()["ai_generated"] is False
    assert created.json()["verification_status"] == "unverified"
    assert created.json()["created_by_user_id"] is not None
    assert created.json()["date_label"] == "August 20, 2004 at 6:30 PM"
    assert created.json()["occurred_time"] == "18:30:00"

    same_day_earlier = await client.post(
        f"/api/v1/cases/{case_id}/timeline",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2004-08-20",
            "occurred_time": "07:15",
            "title": "Morning record located",
            "description": "This earlier time was added after the evening event.",
        },
    )
    assert same_day_earlier.status_code == 201

    earlier = await client.post(
        f"/api/v1/cases/{case_id}/timeline",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2003-02-11",
            "title": "Earlier record located",
            "description": "This event was added after the later event.",
        },
    )
    assert earlier.status_code == 201
    opened = await client.get(f"/api/v1/cases/{case_id}")
    assert [event["title"] for event in opened.json()["timeline"]] == [
        "Earlier record located",
        "Morning record located",
        "Journal entry recorded",
    ]
    assert opened.json()["timeline"][0]["occurred_on"] == "2003-02-11"
    chronological_ids = [event["id"] for event in opened.json()["timeline"]]

    reordered = await client.put(
        f"/api/v1/cases/{case_id}/timeline/order",
        headers={"X-CSRF-Token": token},
        json={"event_ids": list(reversed(chronological_ids))},
    )
    assert reordered.status_code == 204
    opened = await client.get(f"/api/v1/cases/{case_id}")
    assert [event["title"] for event in opened.json()["timeline"]] == [
        "Journal entry recorded",
        "Morning record located",
        "Earlier record located",
    ]
    assert [event["position"] for event in opened.json()["timeline"]] == [0, 1, 2]

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    outsider = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "timeline-outsider@example.com",
            "username": "timeline_outsider",
            "display_name": "Timeline Outsider",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert outsider.status_code == 201
    forbidden = await client.put(
        f"/api/v1/cases/{case_id}/timeline/order",
        headers={"X-CSRF-Token": token},
        json={"event_ids": chronological_ids},
    )
    assert forbidden.status_code == 403


async def test_private_case_requires_verified_account_and_is_owner_only(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "private-owner@example.com",
            "username": "private_owner",
            "display_name": "Private Owner",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    payload = {
        "victim_names": "Private Northpoint Case",
        "creation_mode": "manual",
        "summary": "A private investigator-authored case overview for controlled collaboration.",
        "banner_template": "/case-banners/archive-room.jpg",
        "privacy": "private",
    }

    denied = await client.post("/api/v1/cases", headers={"X-CSRF-Token": token}, json=payload)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "email_verification_required"

    async with SessionFactory() as db:
        owner = await db.scalar(select(User).where(User.username == "private_owner"))
        assert owner
        owner.is_verified = True
        await db.commit()

    created = await client.post("/api/v1/cases", headers={"X-CSRF-Token": token}, json=payload)
    assert created.status_code == 202
    private_case = created.json()
    assert private_case["privacy"] == "private"
    assert private_case["is_owner"] is True
    assert private_case["owner"]["username"] == "private_owner"

    sitemap_response = await client.get("/sitemap.xml")
    assert f"/cases/{private_case['id']}" not in sitemap_response.text

    public_search = await client.get("/api/v1/cases?q=Northpoint")
    assert public_search.status_code == 200
    assert public_search.json()["items"] == []
    assert public_search.json()["total"] == 0
    following = await client.get("/api/v1/cases/following")
    assert following.json() == []
    mine = await client.get("/api/v1/cases/mine")
    assert mine.json()[0]["id"] == private_case["id"]
    assert mine.json()[0]["is_owner"] is True

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "private-outsider@example.com",
            "username": "private_outsider",
            "display_name": "Private Outsider",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )

    hidden = await client.get(f"/api/v1/cases/{private_case['id']}")
    assert hidden.status_code == 404
    hidden_view = await client.post(
        f"/api/v1/cases/{private_case['id']}/view", headers={"X-CSRF-Token": token}
    )
    assert hidden_view.status_code == 404
    hidden_evidence = await client.get(f"/api/v1/cases/{private_case['id']}/evidence")
    assert hidden_evidence.status_code == 404
    privacy_change = await client.patch(
        f"/api/v1/cases/{private_case['id']}/privacy",
        headers={"X-CSRF-Token": token},
        json={"privacy": "public"},
    )
    assert privacy_change.status_code == 404
    admin_cases = await client.get("/api/v1/admin/cases")
    assert admin_cases.status_code == 403
