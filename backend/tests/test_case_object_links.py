import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.cases import routes as case_routes

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


async def test_new_case_objects_can_link_people_and_evidence(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    headers = {"X-CSRF-Token": token}
    await client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "email": "links@example.com",
            "username": "links_user",
            "display_name": "Link Researcher",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    case_id = (
        await client.post(
            "/api/v1/cases",
            headers=headers,
            json={"victim_names": "Fictional Linked Records Case"},
        )
    ).json()["id"]
    person = await client.post(
        f"/api/v1/cases/{case_id}/people",
        headers=headers,
        json={"name": "Morgan Vale", "role": "Witness", "category": "witness"},
    )
    evidence = await client.post(
        f"/api/v1/cases/{case_id}/evidence/links",
        headers=headers,
        json={
            "title": "Public trail bulletin",
            "url": "https://example.gov/trail-bulletin",
            "evidence_type": "article",
        },
    )
    person_id = person.json()["id"]
    evidence_id = evidence.json()["id"]

    event = await client.post(
        f"/api/v1/cases/{case_id}/timeline",
        headers=headers,
        json={
            "occurred_on": "2004-08-20",
            "title": "Witness reached the trailhead",
            "description": "The public bulletin records the reported arrival.",
            "person_ids": [person_id],
            "evidence_ids": [evidence_id],
        },
    )
    thread = await client.post(
        f"/api/v1/cases/{case_id}/discussions",
        headers=headers,
        json={
            "title": "Check the reported arrival",
            "body": "Compare the witness account with the public bulletin.",
            "person_ids": [person_id],
            "evidence_ids": [evidence_id],
        },
    )
    location = await client.post(
        f"/api/v1/cases/{case_id}/locations",
        headers=headers,
        json={
            "name": "North trailhead",
            "description": "The public location named in the bulletin.",
            "latitude": 45.5152,
            "longitude": -122.6784,
            "person_ids": [person_id],
            "evidence_ids": [evidence_id],
        },
    )

    for response in (event, thread, location):
        assert response.status_code == 201
        assert response.json()["people"][0]["id"] == person_id
        assert response.json()["evidence"][0]["id"] == evidence_id

    assert (await client.get(f"/api/v1/cases/{case_id}/people")).json()[0]["id"] == person_id
    assert (await client.get(f"/api/v1/cases/{case_id}")).json()["timeline"][0]["people"][0]["id"] == person_id
    assert (await client.get(f"/api/v1/cases/{case_id}/discussions")).json()["items"][0]["people"][0]["id"] == person_id
    assert (await client.get(f"/api/v1/cases/{case_id}/locations")).json()[0]["people"][0]["id"] == person_id
