"""Discover, generate, and publish a case through live web search."""

import argparse
import asyncio
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cases.models import Case, CaseGenerationJob, CaseSource
from app.cases.tasks import _generate_case
from app.config.settings import get_settings
from app.db import models as _models  # noqa: F401  Register all FK targets.
from app.db.seed import SCHEDULED_CASE_OWNER_EMAIL
from app.users.models import User

logger = structlog.get_logger()
Lane = Literal["recent", "historical", "paranormal"]


@dataclass(frozen=True)
class Candidate:
    source_type: str
    external_id: str
    title: str
    year: int | None
    location: str | None
    source_url: str
    source_name: str
    context: str
    score: int
    source_payload: dict[str, object]
    published_at: datetime | None = None


class DiscoveryProposal(BaseModel):
    title: str
    year: int | None
    location: str | None
    published_date: date | None
    source_urls: list[str]
    reason: str
    relevance_score: int


class DiscoveryResult(BaseModel):
    candidates: list[DiscoveryProposal]


def _canonical_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    hostname = parsed.hostname.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", hostname, path, "", ""))


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def _searched_urls(output: list[Any]) -> dict[str, str]:
    """Only trust URLs returned as web search sources or citations."""
    found: dict[str, str] = {}

    def remember(value: Any) -> None:
        url = _field(value, "url")
        if isinstance(url, str):
            canonical = _canonical_url(url)
            if canonical:
                found.setdefault(canonical, url)

    for item in output:
        if _field(item, "type") == "web_search_call":
            sources = _field(_field(item, "action"), "sources")
            if isinstance(sources, list):
                for source in sources:
                    remember(source)
        elif _field(item, "type") == "message":
            content = _field(item, "content")
            if isinstance(content, list):
                for part in content:
                    annotations = _field(part, "annotations")
                    if isinstance(annotations, list):
                        for annotation in annotations:
                            if _field(annotation, "type") == "url_citation":
                                remember(annotation)
    return found


def _candidate(proposal: DiscoveryProposal, searched: dict[str, str], lane: Lane, now: datetime) -> Candidate | None:
    title = proposal.title.strip()
    if not title or len(title) > 220 or not proposal.reason.strip():
        return None
    if lane == "recent":
        if proposal.published_date is None:
            return None
        age = (now.date() - proposal.published_date).days
        if age < 0 or age > 30:
            return None
    elif lane == "historical" and (proposal.year is None or proposal.year > now.year - 10 or proposal.year < 1800):
        return None
    elif lane == "paranormal" and (proposal.year is None or proposal.year > now.year or proposal.year < 1800):
        return None

    urls: list[str] = []
    domains: set[str] = set()
    for proposed_url in proposal.source_urls:
        canonical = _canonical_url(proposed_url)
        if canonical and canonical in searched and canonical not in urls:
            urls.append(canonical)
            domains.add(urlsplit(canonical).hostname or "")
    if len(domains) < (2 if lane in ("recent", "paranormal") else 1):
        return None

    identity = f"{title.casefold()}|{proposal.year or ''}"
    external_id = hashlib.sha256(identity.encode()).hexdigest()
    primary = urls[0]
    score = max(0, min(proposal.relevance_score, 100)) + 5 * min(len(domains), 3)
    if lane == "recent":
        score += 30 - age
    return Candidate(
        source_type="web_discovery",
        external_id=external_id,
        title=title,
        year=proposal.year,
        location=proposal.location,
        source_url=searched[primary],
        source_name=urlsplit(primary).hostname or "Online source",
        context=f"Discovered through live web search. {proposal.reason.strip()}\nSources:\n" + "\n".join(urls),
        score=score,
        source_payload={
            "title": title,
            "year": proposal.year,
            "location": proposal.location,
            "published_date": proposal.published_date.isoformat() if proposal.published_date else None,
            "source_urls": urls,
            "reason": proposal.reason.strip(),
        },
        published_at=datetime.combine(proposal.published_date, datetime.min.time(), UTC)
        if proposal.published_date
        else None,
    )


def run_key(lane: Lane, now: datetime) -> str:
    if lane == "paranormal":
        return f"{lane}:{now.date().isoformat()}"
    slot = "am" if now.hour < 12 else "pm"
    return f"{lane}:{now.date().isoformat()}:{slot}"


async def discover_candidates(
    client: AsyncOpenAI, model: str, lane: Lane, now: datetime, existing_titles: list[str]
) -> list[Candidate]:
    if lane == "recent":
        task = (
            "Find public, unresolved or high-interest criminal cases with meaningful developments REPORTED "
            "in the last 30 days. Search current news and official releases across different jurisdictions. "
            "published_date is the date of the current report, not the original incident. Give each candidate "
            "at least two independent reporting or official source domains. Rank by public relevance, source "
            "quality, and recency."
        )
    elif lane == "historical":
        task = (
            "Find famous historical or cold criminal cases whose original incident was at least 10 years ago. "
            "Search online archives, court records, official histories, and established reporting. Explore "
            "different regions and decades. year is the original incident year, not the article date. "
            "Rank by public interest, historical importance, and quality of available sources."
        )
    else:
        task = (
            "Find specific, publicly documented paranormal or unexplained incidents, such as UFO/UAP reports, "
            "alleged hauntings, or Men in Black accounts. These are examples of topics, not a fixed case list. "
            "Search live archives, official records when available, and established reporting across different "
            "places and periods. Give each candidate an identifiable incident year and at least two independent "
            "source domains. Rank by public interest and source quality. Describe reported claims as claims; "
            "do not present a supernatural explanation as established fact. Exclude fictional stories, generic "
            "folklore without a documented incident, and cases based only on rumor sites."
        )
    response = await client.responses.parse(
        model=model,
        tools=[{"type": "web_search", "search_context_size": "high"}],
        tool_choice="required",
        include=["web_search_call.action.sources"],
        max_tool_calls=10,
        instructions=(
            "You select candidates for a case research workspace. Search the live web now. Return 5 to 10 "
            "distinct public cases in ranked order, each with exact HTTPS source URLs that you found in "
            "search results. Do not invent URLs, dates, case names, or facts. Exclude rumors, private personal "
            "information, and unsupported accusations. Prefer official records and established reporting. "
            "Use neutral titles and concise reasons. Avoid cases already present in the supplied title list. " + task
        ),
        input=f"Today's UTC date: {now.date().isoformat()}\nExisting case titles to avoid:\n"
        + "\n".join(existing_titles[:150]),
        text_format=DiscoveryResult,
    )
    if response.output_parsed is None:
        raise RuntimeError("Web search returned no structured case candidates")
    searched = _searched_urls(response.output)
    if not searched:
        raise RuntimeError("Web search returned no inspectable source URLs")
    candidates: dict[str, Candidate] = {}
    for proposal in response.output_parsed.candidates:
        candidate = _candidate(proposal, searched, lane, now)
        if candidate:
            candidates.setdefault(candidate.external_id, candidate)
    return sorted(candidates.values(), key=lambda item: (-item.score, item.external_id))


async def select_candidate(db: AsyncSession, candidates: list[Candidate]) -> Candidate | None:
    for candidate in candidates:
        imported = await db.scalar(
            select(CaseSource.id).where(
                CaseSource.source_type == candidate.source_type,
                CaseSource.external_id == candidate.external_id,
            )
        )
        if imported:
            continue
        source_url = await db.scalar(select(CaseSource.id).where(CaseSource.source_url == candidate.source_url))
        if source_url:
            continue
        existing = await db.scalar(
            select(Case.id).where(
                (func.lower(Case.title) == candidate.title.casefold())
                | (func.lower(Case.victim_names) == candidate.title.casefold()),
            )
        )
        if existing:
            continue
        return candidate
    return None


async def create_draft(
    db: AsyncSession, candidate: Candidate, scheduled_run_key: str
) -> tuple[uuid.UUID, uuid.UUID] | None:
    owner = await db.scalar(select(User).where(User.email == SCHEDULED_CASE_OWNER_EMAIL))
    if owner is None:
        raise RuntimeError("Scheduled case owner is missing; run the database seed first")
    case_id = uuid.uuid4()
    job_id = uuid.uuid4()
    slug = re.sub(r"[^a-z0-9]+", "-", candidate.title.lower()).strip("-")[:140] or "case"
    try:
        async with db.begin_nested():
            db.add(
                Case(
                    id=case_id,
                    slug=f"{slug}-{str(case_id)[:8]}",
                    title=candidate.title,
                    victim_names=candidate.title,
                    year=candidate.year,
                    location=candidate.location,
                    intake_notes=candidate.context,
                    privacy="private",
                    status="draft",
                    ai_research_status="queued",
                    counts_toward_weekly_limit=False,
                    created_by_user_id=owner.id,
                )
            )
            db.add(CaseGenerationJob(id=job_id, case_id=case_id))
            db.add(
                CaseSource(
                    case_id=case_id,
                    source_type=candidate.source_type,
                    external_id=candidate.external_id,
                    source_url=candidate.source_url,
                    source_name=candidate.source_name,
                    source_payload=candidate.source_payload,
                    source_published_at=candidate.published_at,
                    source_updated_at=None,
                )
            )
            db.add(
                CaseSource(
                    case_id=case_id,
                    source_type="scheduled_run",
                    external_id=scheduled_run_key,
                    source_url=candidate.source_url,
                    source_name="Case Theory scheduler",
                    source_payload={"run_key": scheduled_run_key},
                    source_published_at=None,
                    source_updated_at=None,
                )
            )
            await db.flush()
    except IntegrityError:
        # A concurrent schedule invocation may have claimed the same source ID.
        await db.rollback()
        claimed = await db.scalar(
            select(CaseSource.id).where(
                (CaseSource.source_type == candidate.source_type) & (CaseSource.external_id == candidate.external_id)
                | (CaseSource.source_type == "scheduled_run") & (CaseSource.external_id == scheduled_run_key),
            )
        )
        if claimed:
            return None
        raise
    await db.commit()
    return case_id, job_id


async def pending_run(db: AsyncSession, case_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID] | None:
    """Resume a case claimed before research began after a process interruption."""
    case = await db.get(Case, case_id)
    job = await db.scalar(
        select(CaseGenerationJob)
        .where(CaseGenerationJob.case_id == case_id)
        .order_by(CaseGenerationJob.created_at.desc())
    )
    if case is None or job is None or case.ai_research_status != "queued" or job.status != "queued":
        return None
    return case.id, job.id


async def run(lane: Lane, *, dry_run: bool = False) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    scheduled_run_key = run_key(lane, now)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            existing_case_id = (
                None
                if dry_run
                else await db.scalar(
                    select(CaseSource.case_id).where(
                        CaseSource.source_type == "scheduled_run",
                        CaseSource.external_id == scheduled_run_key,
                    )
                )
            )
            if existing_case_id:
                created = await pending_run(db, existing_case_id)
                if created is None:
                    logger.info("scheduled_case_run_already_claimed", lane=lane, run_key=scheduled_run_key)
                    return
                source_id = "existing"
            else:
                if not settings.openai_api_key:
                    raise RuntimeError("OPENAI_API_KEY is required for scheduled case discovery")
                existing_titles = list(
                    (await db.scalars(select(Case.title).order_by(Case.created_at.desc()).limit(150))).all()
                )
                candidates = await discover_candidates(
                    AsyncOpenAI(api_key=settings.openai_api_key), settings.ai_text_model, lane, now, existing_titles
                )
                candidate = await select_candidate(db, candidates)
                if candidate is None:
                    logger.info("scheduled_case_no_candidate", lane=lane)
                    return
                if dry_run:
                    logger.info(
                        "scheduled_case_preview", lane=lane, title=candidate.title, source_url=candidate.source_url
                    )
                    return
                created = await create_draft(db, candidate, scheduled_run_key)
                source_id = candidate.external_id
        if created is None:
            logger.info("scheduled_case_already_claimed", lane=lane, source_id=source_id)
            return
        case_id, job_id = created
        logger.info("scheduled_case_research_start", lane=lane, case_id=str(case_id), source_id=source_id)
        await _generate_case(case_id, job_id)
        logger.info("scheduled_case_research_complete", lane=lane, case_id=str(case_id))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and publish one scheduled case")
    parser.add_argument("lane", choices=("recent", "historical", "paranormal"))
    parser.add_argument("--dry-run", action="store_true", help="Select a candidate without creating a case")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.lane, dry_run=arguments.dry_run))


if __name__ == "__main__":
    main()
