import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import SessionFactory
from app.reels.models import ReelDraft
from app.reels.schemas import ReelDraftCreate

pytestmark = pytest.mark.usefixtures("paid_signups")


def test_reel_schema_accepts_three_minute_short_timeline() -> None:
    reel = ReelDraftCreate.model_validate(
        {
            "title": "A documented case",
            "hook": "The record leaves an unresolved question.",
            "narration": "A sufficiently detailed narration for the documented case timeline.",
            "caption": "Review the documented sources.",
            "duration_seconds": 70,
            "scenes": [
                {
                    "start_second": 0,
                    "end_second": 55,
                    "on_screen_text": "The documented case",
                    "visual_direction": "Show the sourced case timeline.",
                },
                {
                    "start_second": 55,
                    "end_second": 70,
                    "on_screen_text": "Explore and collaborate",
                    "visual_direction": "Show the app and final brand card.",
                },
            ],
            "sources": [{"title": "Official source", "url": "https://example.gov/case"}],
        }
    )

    assert reel.duration_seconds == 70


async def test_reel_draft_create_list_and_approve(client: AsyncClient) -> None:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    headers = {"X-CSRF-Token": token}
    registration = await client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "email": "reels@example.com",
            "username": "reel_researcher",
            "display_name": "Reel Researcher",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registration.status_code == 201
    case_response = await client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "victim_names": "Fictional Reel Case",
            "creation_mode": "manual",
            "summary": "A sourced fictional case used to test reel drafting.",
            "banner_template": "/case-banners/archive-room.jpg",
            "privacy": "private",
        },
    )
    assert case_response.status_code == 202
    case_id = case_response.json()["id"]
    payload = {
        "title": "A documented turning point",
        "hook": "The public timeline changed after one official update.",
        "narration": "The official record documents a timeline update while leaving a central question unresolved.",
        "caption": "Review the public record and the complete Case Theory timeline.",
        "duration_seconds": 30,
        "scenes": [
            {
                "start_second": 0,
                "end_second": 10,
                "on_screen_text": "The timeline changed",
                "visual_direction": "Show a neutral case-file title card.",
            },
            {
                "start_second": 10,
                "end_second": 30,
                "on_screen_text": "Review the source",
                "visual_direction": "Show a timeline graphic and source credit.",
            },
        ],
        "sources": [{"title": "Official case page", "url": "https://example.gov/case"}],
    }
    created = await client.post(f"/api/v1/cases/{case_id}/reels", headers=headers, json=payload)
    assert created.status_code == 201
    reel = created.json()
    assert reel["status"] == "draft"
    assert reel["scenes"][-1]["end_second"] == 30

    listed = await client.get(f"/api/v1/cases/{case_id}/reels")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [reel["id"]]

    updated = await client.patch(
        f"/api/v1/cases/{case_id}/reels/{reel['id']}",
        headers=headers,
        json={**payload, "status": "approved", "title": "Approved turning point"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "approved"
    assert updated.json()["title"] == "Approved turning point"

    async with SessionFactory() as db:
        stored = await db.scalar(select(ReelDraft).where(ReelDraft.id == uuid.UUID(reel["id"])))
        assert stored is not None
        stored.automated = True
        stored.duration_seconds = 34
        await db.commit()
    listed_legacy_automated = await client.get(f"/api/v1/cases/{case_id}/reels")
    assert listed_legacy_automated.status_code == 200
    assert listed_legacy_automated.json()[0]["scenes"][-1] == {
        "start_second": 30,
        "end_second": 34,
        "on_screen_text": "Explore the full case",
        "visual_direction": "Brand end card",
    }
    read_only = await client.patch(
        f"/api/v1/cases/{case_id}/reels/{reel['id']}",
        headers=headers,
        json={**payload, "status": "approved"},
    )
    assert read_only.status_code == 409
    assert read_only.json()["error"]["code"] == "automated_reel_read_only"


async def test_reel_draft_rejects_gapped_scenes(client: AsyncClient) -> None:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    headers = {"X-CSRF-Token": token}
    await client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "email": "reel-validation@example.com",
            "username": "reel_validator",
            "display_name": "Reel Validator",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    case_response = await client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "victim_names": "Validation Case",
            "creation_mode": "manual",
            "summary": "A fictional case for validating reel scene timing.",
            "banner_template": "/case-banners/archive-room.jpg",
            "privacy": "private",
        },
    )
    case_id = case_response.json()["id"]
    response = await client.post(
        f"/api/v1/cases/{case_id}/reels",
        headers=headers,
        json={
            "title": "Invalid scene timing",
            "hook": "This draft contains a timeline gap.",
            "narration": "This narration is long enough for schema validation but the scene timing is not contiguous.",
            "caption": "Invalid draft",
            "duration_seconds": 30,
            "scenes": [
                {"start_second": 0, "end_second": 10, "on_screen_text": "Start", "visual_direction": "Title card."},
                {"start_second": 12, "end_second": 30, "on_screen_text": "End", "visual_direction": "End card."},
            ],
            "sources": [{"title": "Official", "url": "https://example.gov/case"}],
        },
    )
    assert response.status_code == 422
