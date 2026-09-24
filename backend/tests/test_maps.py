import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.cases import routes as case_routes

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


async def test_user_can_add_and_review_case_locations(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "map@example.com",
            "username": "map_user",
            "display_name": "Map Researcher",
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
            json={"victim_names": "Fictional River Trail Case"},
        )
    ).json()["id"]

    created = await client.post(
        f"/api/v1/cases/{case_id}/locations",
        headers={"X-CSRF-Token": token},
        json={
            "name": "North trailhead",
            "description": "Public parking area named in the trail bulletin.",
            "latitude": 45.5152,
            "longitude": -122.6784,
            "location_type": "last_seen",
            "occurred_on": "2004-08-20",
            "precision": "approximate",
            "verification_status": "unverified",
            "source_url": "https://example.gov/trail-bulletin",
        },
    )
    assert created.status_code == 201
    assert created.json()["ai_suggested"] is False
    assert created.json()["occurred_on"] == "2004-08-20"

    locations = await client.get(f"/api/v1/cases/{case_id}/locations")
    assert locations.status_code == 200
    assert locations.json()[0]["name"] == "North trailhead"

    rejected = await client.patch(
        f"/api/v1/cases/{case_id}/locations/{created.json()['id']}",
        headers={"X-CSRF-Token": token},
        json={"review_status": "rejected"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert (await client.get(f"/api/v1/cases/{case_id}/locations")).json() == []
