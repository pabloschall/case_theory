import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.cases import routes as case_routes

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


async def test_flat_thread_comments_and_reaction_toggle(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    csrf_response = await client.get("/api/v1/auth/csrf")
    token = csrf_response.json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "discussion@example.com",
            "username": "discussion_user",
            "display_name": "Discussion User",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    case_response = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={"victim_names": "Fictional Discussion Case"},
    )
    case_id = case_response.json()["id"]

    created = await client.post(
        f"/api/v1/cases/{case_id}/discussions",
        headers={"X-CSRF-Token": token},
        json={
            "title": "Review the trail records",
            "body": "Which public records support the stated route?",
            "thread_type": "evidence",
        },
    )
    assert created.status_code == 201
    thread_id = created.json()["id"]

    commented = await client.post(
        f"/api/v1/cases/{case_id}/discussions/{thread_id}/comments",
        headers={"X-CSRF-Token": token},
        json={"body": "The park bulletin provides a dated reference."},
    )
    assert commented.status_code == 201
    comment_id = commented.json()["comments"][0]["id"]

    nested = await client.post(
        f"/api/v1/cases/{case_id}/discussions/{thread_id}/comments",
        headers={"X-CSRF-Token": token},
        json={"body": "Attempted nested reply", "parent_comment_id": comment_id},
    )
    assert nested.status_code == 422

    reacted = await client.post(
        f"/api/v1/cases/{case_id}/discussions/{thread_id}/comments/{comment_id}/reactions",
        headers={"X-CSRF-Token": token},
        json={"emoji": "🔎"},
    )
    assert reacted.status_code == 200
    assert reacted.json()["comments"][0]["reactions"] == [
        {"emoji": "🔎", "count": 1, "reacted_by_me": True}
    ]

    unreacted = await client.post(
        f"/api/v1/cases/{case_id}/discussions/{thread_id}/comments/{comment_id}/reactions",
        headers={"X-CSRF-Token": token},
        json={"emoji": "🔎"},
    )
    assert unreacted.status_code == 200
    assert unreacted.json()["comments"][0]["reactions"] == []

    threads = await client.get(f"/api/v1/cases/{case_id}/discussions")
    assert threads.status_code == 200
    assert threads.json()["items"][0]["title"] == "Review the trail records"
    assert threads.json()["items"][0]["thread_type"] == "evidence"
    assert threads.json()["items"][0]["vote_count"] == 0
    assert threads.json()["items"][0]["voted_by_me"] is False
    assert len(threads.json()["items"][0]["comments"]) == 1
    assert threads.json()["total"] == 1
    assert threads.json()["active_count"] == 1
    assert threads.json()["comment_count"] == 1

    second = await client.post(
        f"/api/v1/cases/{case_id}/discussions",
        headers={"X-CSRF-Token": token},
        json={
            "title": "Compare the ranger notes",
            "body": "Do the independently published notes agree with the bulletin?",
            "thread_type": "question",
        },
    )
    assert second.status_code == 201
    voted = await client.post(
        f"/api/v1/cases/{case_id}/discussions/{thread_id}/vote",
        headers={"X-CSRF-Token": token},
    )
    assert voted.status_code == 200
    assert voted.json() == {"vote_count": 1, "voted_by_me": True}
    first_page = await client.get(f"/api/v1/cases/{case_id}/discussions?limit=1")
    assert first_page.json()["total"] == 2
    assert first_page.json()["has_more"] is True
    assert first_page.json()["next_cursor"]
    assert first_page.json()["items"][0]["id"] == thread_id
    assert first_page.json()["items"][0]["vote_count"] == 1
    assert first_page.json()["items"][0]["voted_by_me"] is True
    second_page = await client.get(
        f"/api/v1/cases/{case_id}/discussions",
        params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
    )
    assert second_page.json()["has_more"] is False
    assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]
    unvoted = await client.post(
        f"/api/v1/cases/{case_id}/discussions/{thread_id}/vote",
        headers={"X-CSRF-Token": token},
    )
    assert unvoted.status_code == 200
    assert unvoted.json() == {"vote_count": 0, "voted_by_me": False}
