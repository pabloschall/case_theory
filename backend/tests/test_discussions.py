import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.ai.schemas import ResearchedSource, ThreadResearchResult
from app.cases import routes as case_routes
from app.discussions import service as discussion_service

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


class StubThreadResearcher:
    calls: list[dict[str, str]] = []

    def __init__(self, _: object) -> None:
        pass

    async def research(self, **context: str) -> ThreadResearchResult:
        self.calls.append(context)
        return ThreadResearchResult(
            body=(
                "Public reporting documents the known timeline, but it does not establish "
                "who was responsible. The proposed idea remains an inference."
            ),
            sources=[
                ResearchedSource(
                    title="Official public case record",
                    url="https://example.gov/cases/fictional-discussion",
                )
            ],
        )


async def test_ai_search_creates_an_unproven_sourced_theory(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    StubThreadResearcher.calls = []
    monkeypatch.setattr(discussion_service, "OpenAIThreadResearcher", StubThreadResearcher)
    csrf_response = await client.get("/api/v1/auth/csrf")
    token = csrf_response.json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "theory@example.com",
            "username": "theory_user",
            "display_name": "Theory User",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    summary = "The public record leaves several events unresolved and open to careful discussion."
    case_response = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Fictional Theory Case",
            "creation_mode": "manual",
            "summary": summary,
            "banner_template": "/case-banners/archive-room.jpg",
        },
    )
    case_id = case_response.json()["id"]

    created = await client.post(
        f"/api/v1/cases/{case_id}/discussions",
        headers={"X-CSRF-Token": token},
        json={
            "title": "The husband did it",
            "thread_type": "dispute",
            "ai_search": True,
        },
    )

    assert created.status_code == 201
    thread = created.json()
    assert thread["title"] == "The husband did it"
    assert thread["thread_type"] == "theory"
    assert thread["ai_generated"] is True
    assert thread["review_status"] == "suggested"
    assert thread["body"].startswith("Unproven theory:")
    assert "not proof" in thread["body"]
    assert thread["sources"][0]["url"] == ("https://example.gov/cases/fictional-discussion")
    assert StubThreadResearcher.calls == [
        {
            "case_title": "Fictional Theory Case",
            "case_summary": summary,
            "thread_title": "The husband did it",
        }
    ]


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
    assert reacted.json()["comments"][0]["reactions"] == [{"emoji": "🔎", "count": 1, "reacted_by_me": True}]

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
