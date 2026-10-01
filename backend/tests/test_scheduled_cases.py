from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import app.scheduled_cases as scheduled_cases
from app.cases.models import Case, CaseGenerationJob, CaseSource
from app.cases.service import CaseService, to_case_read
from app.db.seed import SCHEDULED_CASE_OWNER_EMAIL, seed_scheduled_case_owner
from app.db.session import SessionFactory
from app.scheduled_cases import (
    DiscoveryProposal,
    DiscoveryResult,
    create_draft,
    discover_candidates,
    pending_run,
    run_key,
    select_candidate,
)
from app.users.models import User

NOW = datetime(2026, 9, 30, tzinfo=UTC)
FIRST = "https://court.gov.example/cases/archive-1"
SECOND = "https://news.example/articles/archive-1"


def proposal(
    *, published_date: date | None, year: int | None = 1999, urls: list[str] | None = None
) -> DiscoveryProposal:
    return DiscoveryProposal(
        title="Archive Case One",
        year=year,
        location="Phoenix, Arizona",
        published_date=published_date,
        source_urls=urls if urls is not None else [FIRST, SECOND],
        reason="Publicly documented case with material evidence.",
        relevance_score=85,
    )


def mock_client(proposals: list[DiscoveryProposal]) -> SimpleNamespace:
    response = SimpleNamespace(
        output_parsed=DiscoveryResult(candidates=proposals),
        model_dump=lambda: {
            "output": [
                {
                    "type": "web_search_call",
                    "action": {"sources": [{"url": FIRST}, {"url": SECOND}]},
                }
            ]
        },
    )
    return SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=response)))


async def test_both_lanes_search_live_and_validate_sources() -> None:
    recent_client = mock_client(
        [
            proposal(published_date=NOW.date() - timedelta(days=2)),
            proposal(published_date=NOW.date() - timedelta(days=2), urls=["https://invented.example/case"]),
        ]
    )
    recent = await discover_candidates(recent_client, "gpt-5-mini", "recent", NOW, ["Existing Case"])
    assert len(recent) == 1
    assert recent[0].source_type == "web_discovery"
    assert recent[0].source_url == FIRST
    assert recent[0].source_payload["source_urls"] == [FIRST, SECOND]
    recent_kwargs = recent_client.responses.parse.await_args.kwargs
    assert recent_kwargs["tools"] == [{"type": "web_search", "search_context_size": "high"}]
    assert recent_kwargs["tool_choice"] == "required"
    assert recent_kwargs["include"] == ["web_search_call.action.sources"]
    assert "Existing Case" in recent_kwargs["input"]

    historical_client = mock_client([proposal(published_date=None, year=1999, urls=[FIRST])])
    historical = await discover_candidates(historical_client, "gpt-5-mini", "historical", NOW, [])
    assert len(historical) == 1
    assert historical[0].external_id == recent[0].external_id
    assert historical[0].source_name == "court.gov.example"
    assert "historical or cold" in historical_client.responses.parse.await_args.kwargs["instructions"]


async def test_discovery_rejects_stale_news_and_nonhistorical_cases() -> None:
    old_news = mock_client([proposal(published_date=NOW.date() - timedelta(days=31))])
    assert await discover_candidates(old_news, "gpt-5-mini", "recent", NOW, []) == []
    single_source = mock_client([proposal(published_date=NOW.date(), urls=[FIRST])])
    assert await discover_candidates(single_source, "gpt-5-mini", "recent", NOW, []) == []
    too_new = mock_client([proposal(published_date=None, year=2020)])
    assert await discover_candidates(too_new, "gpt-5-mini", "historical", NOW, []) == []
    assert run_key("recent", NOW) == "recent:2026-09-30"
    assert run_key("historical", NOW) == "historical:2026-W40"


async def test_scheduled_draft_is_private_and_source_claim_is_unique() -> None:
    candidate = (
        await discover_candidates(mock_client([proposal(published_date=None)]), "gpt-5-mini", "historical", NOW, [])
    )[0]
    async with SessionFactory() as db:
        await seed_scheduled_case_owner(db)
        await db.commit()
        owner = await db.scalar(select(User).where(User.email == SCHEDULED_CASE_OWNER_EMAIL))
        assert owner is not None and not owner.is_active
        assert await select_candidate(db, [candidate]) == candidate

        created = await create_draft(db, candidate, "historical:2026-W40")
        assert created is not None
        case_id, job_id = created
        case = await db.get(Case, case_id)
        job = await db.get(CaseGenerationJob, job_id)
        source = await db.scalar(
            select(CaseSource).where(CaseSource.case_id == case_id, CaseSource.source_type == "web_discovery")
        )
        assert case is not None and case.privacy == "private" and case.status == "draft"
        assert case.created_by_user_id == owner.id
        assert job is not None and job.status == "queued"
        assert await pending_run(db, case_id) == (case_id, job_id)
        assert source is not None and source.source_url == candidate.source_url
        detail = to_case_read(await CaseService(db).get(case_id), None)
        assert [item.source_type for item in detail.external_sources] == ["web_discovery"]
        assert await select_candidate(db, [candidate]) is None
        assert await create_draft(db, candidate, "historical:2026-W40") is None
        other = scheduled_cases.Candidate(**{**candidate.__dict__, "external_id": "other", "source_url": SECOND})
        assert await create_draft(db, other, "historical:2026-W40") is None
        job.status = "running"
        await db.commit()
        assert await pending_run(db, case_id) is None
        public_cases, total = await CaseService(db).search()
        assert public_cases == [] and total == 0


async def test_scheduled_run_resumes_a_queued_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    key = run_key("historical", datetime.now(UTC))
    candidate = (
        await discover_candidates(mock_client([proposal(published_date=None)]), "gpt-5-mini", "historical", NOW, [])
    )[0]
    async with SessionFactory() as db:
        await seed_scheduled_case_owner(db)
        await db.commit()
        created = await create_draft(db, candidate, key)
        assert created is not None

    generate = AsyncMock()
    monkeypatch.setattr(scheduled_cases, "_generate_case", generate)
    await scheduled_cases.run("historical")
    generate.assert_awaited_once_with(*created)
