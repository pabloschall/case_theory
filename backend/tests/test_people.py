import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.cases import routes as case_routes

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


async def test_people_relationships_review_and_notes(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "people@example.com",
            "username": "people_user",
            "display_name": "People Researcher",
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
            json={"victim_names": "Fictional Harbor Case"},
        )
    ).json()["id"]

    primary = await client.post(
        f"/api/v1/cases/{case_id}/people",
        headers={"X-CSRF-Token": token},
        json={
            "name": "Mara Ellison",
            "role": "Primary subject",
            "category": "primary",
            "is_primary": True,
            "summary": "Last publicly documented near the harbor footpath.",
        },
    )
    witness = await client.post(
        f"/api/v1/cases/{case_id}/people",
        headers={"X-CSRF-Token": token},
        json={"name": "Theo Ward", "role": "Witness", "category": "witness"},
    )
    assert primary.status_code == 201
    assert witness.status_code == 201

    relationship = await client.post(
        f"/api/v1/cases/{case_id}/relationships",
        headers={"X-CSRF-Token": token},
        json={
            "source_person_id": witness.json()["id"],
            "target_person_id": primary.json()["id"],
            "relationship_type": "witnessed",
            "label": "Reported seeing",
            "confidence": 0.82,
            "source_url": "https://example.gov/harbor-report",
            "ai_suggested": True,
        },
    )
    assert relationship.status_code == 201
    assert relationship.json()["review_status"] == "suggested"

    note = await client.post(
        f"/api/v1/cases/{case_id}/people/{primary.json()['id']}/notes",
        headers={"X-CSRF-Token": token},
        json={"body": "Compare this account with the harbor camera timestamps."},
    )
    assert note.status_code == 201
    assert note.json()["author_name"] == "People Researcher"

    people = await client.get(f"/api/v1/cases/{case_id}/people")
    assert people.status_code == 200
    assert people.json()[0]["connection_count"] == 1
    assert people.json()[0]["notes_count"] == 1

    confirmed = await client.patch(
        f"/api/v1/cases/{case_id}/relationships/{relationship.json()['id']}",
        headers={"X-CSRF-Token": token},
        json={"review_status": "confirmed"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["review_status"] == "confirmed"

    evidence = await client.get(f"/api/v1/cases/{case_id}/people/{primary.json()['id']}/evidence")
    assert evidence.status_code == 200
    assert evidence.json() == []
