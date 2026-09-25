import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.ai.chat_research import ChatResearchResponse
from app.ai.schemas import ResearchedSource
from app.cases import routes as case_routes

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubResearcher:
    calls: list[dict[str, object]] = []

    def __init__(self, _: object) -> None:
        pass

    async def answer(self, **context: object) -> ChatResearchResponse:
        self.calls.append(context)
        return ChatResearchResponse(
            answer="The public record does not establish an answer.",
            sources=[ResearchedSource(title="Public record", url="https://example.gov/case")],
        )


async def test_research_chat_uses_stored_case_context_and_returns_sources(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    StubResearcher.calls = []
    monkeypatch.setattr(case_routes, "OpenAIChatResearcher", StubResearcher)
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    headers = {"X-CSRF-Token": token}
    await client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "email": "chat@example.com",
            "username": "chat_researcher",
            "display_name": "Chat Researcher",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    overview = "A carefully documented public case with several questions still unresolved."
    case = await client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "victim_names": "Fictional Research Case",
            "creation_mode": "manual",
            "summary": overview,
            "banner_template": "/case-banners/archive-room.jpg",
        },
    )
    case_id = case.json()["id"]
    response = await client.post(
        f"/api/v1/cases/{case_id}/research-chat",
        headers=headers,
        json={
            "message": "What do officials say?",
            "history": [{"role": "user", "content": "When did this happen?"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["url"] == "https://example.gov/case"
    assert StubResearcher.calls[0]["case_title"] == "Fictional Research Case"
    assert StubResearcher.calls[0]["case_summary"] == overview
    assert StubResearcher.calls[0]["message"] == "What do officials say?"
    assert StubResearcher.calls[0]["history"][0].content == "When did this happen?"
