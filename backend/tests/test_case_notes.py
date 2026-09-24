import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.cases import routes as case_routes

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


async def register(
    client: AsyncClient, token: str, *, email: str, username: str
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": email,
            "username": username,
            "display_name": username.replace("_", " ").title(),
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert response.status_code == 201


async def test_case_notes_are_private_to_their_author(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await register(
        client, token, email="notebook-owner@example.com", username="notebook_owner"
    )
    case_response = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={"victim_names": "Fictional Notebook Case"},
    )
    assert case_response.status_code == 202
    case_id = case_response.json()["id"]

    first = await client.post(
        f"/api/v1/cases/{case_id}/notes",
        headers={"X-CSRF-Token": token},
        json={"title": "Questions about the route", "body": "Compare the trail records."},
    )
    second = await client.post(
        f"/api/v1/cases/{case_id}/notes",
        headers={"X-CSRF-Token": token},
        json={"title": "Follow-up sources", "body": "Request the public ranger bulletin."},
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["author"]["username"] == "notebook_owner"
    assert first.json()["can_edit"] is True

    page_one = await client.get(f"/api/v1/cases/{case_id}/notes", params={"limit": 1})
    assert page_one.status_code == 200
    assert page_one.json()["total"] == 2
    assert page_one.json()["has_more"] is True
    page_two = await client.get(
        f"/api/v1/cases/{case_id}/notes",
        params={"limit": 1, "cursor": page_one.json()["next_cursor"]},
    )
    assert page_two.status_code == 200
    assert page_two.json()["has_more"] is False
    assert page_one.json()["items"][0]["id"] != page_two.json()["items"][0]["id"]

    note_id = first.json()["id"]
    updated = await client.patch(
        f"/api/v1/cases/{case_id}/notes/{note_id}",
        headers={"X-CSRF-Token": token},
        json={"title": "Route questions", "body": "Compare the trail and weather records."},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Route questions"

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    guest_notes = await client.get(f"/api/v1/cases/{case_id}/notes")
    assert guest_notes.status_code == 401

    await register(
        client, token, email="notebook-other@example.com", username="notebook_other"
    )
    other_user_notes = await client.get(f"/api/v1/cases/{case_id}/notes")
    assert other_user_notes.status_code == 200
    assert other_user_notes.json()["items"] == []
    cannot_edit = await client.patch(
        f"/api/v1/cases/{case_id}/notes/{note_id}",
        headers={"X-CSRF-Token": token},
        json={"title": "Changed", "body": "Should never be accepted."},
    )
    assert cannot_edit.status_code == 404


async def test_personal_timeline_is_private_to_its_author(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await register(
        client, token, email="personal-timeline@example.com", username="personal_timeline"
    )
    case_id = (
        await client.post(
            "/api/v1/cases",
            headers={"X-CSRF-Token": token},
            json={"victim_names": "Personal Timeline Case"},
        )
    ).json()["id"]

    created = await client.post(
        f"/api/v1/cases/{case_id}/my-timeline",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2026-09-20",
            "title": "Reviewed the public record",
            "body": "Compared the source dates and recorded an open question.",
        },
    )
    assert created.status_code == 201
    assert created.json()["author"]["username"] == "personal_timeline"
    entry_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/cases/{case_id}/my-timeline/{entry_id}",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2026-09-21",
            "title": "Reviewed the complete public record",
            "body": "Compared all available source dates and recorded an open question.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["occurred_on"] == "2026-09-21"

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    visible = await client.get(f"/api/v1/cases/{case_id}/my-timeline")
    assert visible.status_code == 401

    await register(
        client,
        token,
        email="other-personal-timeline@example.com",
        username="other_personal_timeline",
    )
    other_timeline = await client.get(f"/api/v1/cases/{case_id}/my-timeline")
    assert other_timeline.status_code == 200
    assert other_timeline.json() == []
    cannot_edit = await client.patch(
        f"/api/v1/cases/{case_id}/my-timeline/{entry_id}",
        headers={"X-CSRF-Token": token},
        json={
            "occurred_on": "2026-09-22",
            "title": "Changed",
            "body": "This entry belongs to another user.",
        },
    )
    assert cannot_edit.status_code == 404
