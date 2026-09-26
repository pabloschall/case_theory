import json
import uuid

import pytest
from httpx import AsyncClient
from pydantic import BaseModel
from pytest import MonkeyPatch
from sqlalchemy import select

from app.ai.chat_research import (
    ChatResearchResponse,
    EvidenceActionDraft,
    ResearchAction,
    StructuredEvidenceResearchAnswer,
    StructuredResearchAnswer,
    StructuredThreadResearchAnswer,
    StructuredTimelineResearchAnswer,
    TimelineActionDraft,
    build_research_action,
    requested_action_type,
)
from app.ai.schemas import ResearchedSource
from app.cases import routes as case_routes
from app.db.session import SessionFactory
from app.subscriptions.models import SubscriptionPlan, UserSubscription

pytestmark = pytest.mark.usefixtures("paid_signups")


def test_structured_research_schema_uses_openai_supported_constructs() -> None:
    schema = json.dumps(StructuredResearchAnswer.model_json_schema())
    assert '"oneOf"' not in schema
    assert '"format": "uri"' not in schema


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Can you add that to the timeline?", "timeline"),
        ("Create a discussion thread from this", "thread"),
        ("Save this source as evidence", "evidence"),
        ("What does the timeline say?", None),
    ],
)
def test_requested_action_type_only_matches_explicit_creation_requests(
    message: str, expected: str | None
) -> None:
    assert requested_action_type(message) == expected


@pytest.mark.parametrize(
    "response_type",
    [StructuredTimelineResearchAnswer, StructuredThreadResearchAnswer, StructuredEvidenceResearchAnswer],
)
def test_explicit_action_response_schemas_require_an_action(response_type: type[BaseModel]) -> None:
    schema = response_type.model_json_schema()
    assert "action" in schema["required"]
    assert schema["properties"]["action"].get("default") is None


class StubResearcher:
    calls: list[dict[str, object]] = []

    def __init__(self, _: object) -> None:
        pass

    async def answer(self, **context: object) -> ChatResearchResponse:
        self.calls.append(context)
        return ChatResearchResponse(
            answer="The public record does not establish an answer.",
            sources=[ResearchedSource(title="Public record", url="https://example.gov/case")],
            action=ResearchAction(
                action_type="timeline",
                label="Add to timeline",
                endpoint=f"/cases/{context['case_id']}/timeline",
                payload={
                    "occurred_on": "2024-03-12",
                    "title": "Officials published an update",
                    "description": "The official case page published a dated update.",
                    "evidence_ids": [],
                    "person_ids": [],
                },
            ),
        )


def test_evidence_action_must_use_a_returned_research_source() -> None:
    draft = EvidenceActionDraft(
        action_type="evidence",
        title="Official case page",
        description="A public source consulted by the researcher.",
        url="https://untrusted.example/story",
        evidence_type="article",
    )
    action = build_research_action(
        draft,
        case_id=uuid.uuid4(),
        sources=[ResearchedSource(title="Public record", url="https://example.gov/case")],
    )
    assert action is None


def test_timeline_action_uses_the_case_scoped_endpoint_and_valid_payload() -> None:
    case_id = uuid.uuid4()
    action = build_research_action(
        TimelineActionDraft(
            action_type="timeline",
            occurred_on="2024-03-12",
            title="Officials published an update",
            description="The official case page published a dated update.",
        ),
        case_id=case_id,
        sources=[ResearchedSource(title="Public record", url="https://example.gov/case")],
    )
    assert action is not None
    assert action.endpoint == f"/cases/{case_id}/timeline"
    assert action.payload["occurred_on"] == "2024-03-12"
    assert action.payload["evidence_ids"] == []
    assert action.payload["description"].endswith("https://example.gov/case")


async def test_research_chat_uses_stored_case_context_and_returns_sources(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    StubResearcher.calls = []
    monkeypatch.setattr(case_routes, "OpenAIChatResearcher", StubResearcher)
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    headers = {"X-CSRF-Token": token}
    registration = await client.post(
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
    assert registration.status_code == 201
    user = (await client.get("/api/v1/users/me")).json()
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
            "history": [
                {"role": "user", "content": "When did this happen?"},
                {
                    "role": "assistant",
                    "content": "Officials published an update.",
                    "sources": [{"title": "Public record", "url": "https://example.gov/case"}],
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["url"] == "https://example.gov/case"
    assert response.json()["action"] == {
        "action_type": "timeline",
        "label": "Add to timeline",
        "method": "POST",
        "endpoint": f"/cases/{case_id}/timeline",
        "payload": {
            "occurred_on": "2024-03-12",
            "title": "Officials published an update",
            "description": "The official case page published a dated update.",
            "evidence_ids": [],
            "person_ids": [],
        },
    }
    assert StubResearcher.calls[0]["case_id"] == uuid.UUID(case_id)
    assert StubResearcher.calls[0]["case_title"] == "Fictional Research Case"
    assert StubResearcher.calls[0]["case_summary"] == overview
    assert StubResearcher.calls[0]["message"] == "What do officials say?"
    assert StubResearcher.calls[0]["history"][0].content == "When did this happen?"
    assert StubResearcher.calls[0]["history"][1].sources[0].url == "https://example.gov/case"

    async with SessionFactory() as db:
        free_plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "free"))
        subscription = await db.scalar(
            select(UserSubscription).where(
                UserSubscription.user_id == uuid.UUID(user["id"]),
                UserSubscription.is_active.is_(True),
            )
        )
        assert free_plan is not None
        assert subscription is not None
        subscription.plan_id = free_plan.id
        await db.commit()

    locked = await client.post(
        f"/api/v1/cases/{case_id}/research-chat",
        headers=headers,
        json={"message": "Can a free account search?", "history": []},
    )
    assert locked.status_code == 403
    assert locked.json()["error"]["code"] == "researcher_upgrade_required"
    assert len(StubResearcher.calls) == 1
