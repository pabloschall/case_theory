import asyncio
import uuid
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.openai_provider import OpenAICaseGenerator
from app.cases.models import (
    Case,
    CaseGenerationJob,
    CaseSource,
    CaseSummary,
    Source,
    TimelineEvent,
    TimelineEventSource,
)
from app.cases.timeline_dates import parse_timeline_date, parse_timeline_time
from app.common.timestamps import utc_now
from app.config.settings import get_settings
from app.db import models as _models  # noqa: F401  Register all FK targets for worker mappers.
from app.discussions.models import DiscussionThread, DiscussionThreadSource
from app.evidence.models import Evidence
from app.maps.models import CaseLocation
from app.people.models import Person, PersonRelationship
from app.people.service import _slug
from app.storage.provider import get_storage_provider
from app.workers.celery_app import celery_app


@celery_app.task(name="case.generate", bind=True, max_retries=2)  # type: ignore[untyped-decorator]
def generate_case(self: object, case_id: str, job_id: str) -> None:
    asyncio.run(_generate_case(uuid.UUID(case_id), uuid.UUID(job_id)))


async def _complete_generation(db: AsyncSession, case: Case, job: CaseGenerationJob) -> None:
    case.ai_research_status = "complete"
    case.status = "active"
    job.status = "complete"
    job.completed_at = utc_now()
    scheduled = await db.scalar(
        select(CaseSource.id).where(CaseSource.case_id == case.id, CaseSource.source_type == "scheduled_run")
    )
    if scheduled is not None:
        case.privacy = "public"
    await db.commit()


async def _generate_case(case_id: uuid.UUID, job_id: uuid.UUID) -> None:
    settings = get_settings()
    # Celery executes this coroutine with a fresh event loop for each task. A
    # process-global asyncpg pool can retain connections owned by an older loop,
    # so the worker owns and disposes a task-local engine instead.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            case = await db.scalar(select(Case).where(Case.id == case_id))
            job = await db.scalar(select(CaseGenerationJob).where(CaseGenerationJob.id == job_id))
            if case is None or job is None:
                return
            case.ai_research_status = "researching_sources"
            job.status = "running"
            job.started_at = utc_now()
            job.text_model = settings.ai_text_model
            job.image_model = settings.ai_image_model
            await db.commit()
            try:
                storage = get_storage_provider()
                generator = OpenAICaseGenerator(settings, storage)
                research = await generator.research(case)

                # A successful search stage is persisted before synthesis so its
                # provenance survives a later model or image failure.
                await db.execute(
                    delete(TimelineEvent).where(
                        TimelineEvent.case_id == case.id,
                        TimelineEvent.ai_generated.is_(True),
                    )
                )
                await db.execute(
                    delete(DiscussionThread).where(
                        DiscussionThread.case_id == case.id,
                        DiscussionThread.ai_generated.is_(True),
                    )
                )
                await db.execute(
                    delete(Evidence).where(
                        Evidence.case_id == case.id,
                        Evidence.ai_generated.is_(True),
                    )
                )
                await db.execute(delete(Source).where(Source.case_id == case.id))
                source_records = [
                    Source(
                        case_id=case.id,
                        url=item.url,
                        canonical_url=item.url,
                        title=item.title,
                        position=position,
                        publisher=_publisher(item.url),
                        source_type=_source_type(item.url),
                        reliability_metadata={"classification_basis": "URL and publisher provenance only"},
                    )
                    for position, item in enumerate(research.sources, start=1)
                ]
                db.add_all(source_records)
                case.ai_research_status = "generating_overview"
                await db.commit()

                draft = await generator.generate_draft(case, research)
                await db.execute(
                    update(CaseSummary)
                    .where(CaseSummary.case_id == case.id, CaseSummary.is_current.is_(True))
                    .values(is_current=False)
                )
                latest_version = await db.scalar(
                    select(func.max(CaseSummary.version)).where(CaseSummary.case_id == case.id)
                )
                case.title = draft.title
                case.cover_image_prompt = draft.banner_prompt
                db.add(
                    CaseSummary(
                        case_id=case.id,
                        version=(latest_version or 0) + 1,
                        body=draft.overview,
                        ai_model=settings.ai_text_model,
                    )
                )
                for event in draft.timeline:
                    source_indexes = sorted(
                        {number - 1 for number in event.source_numbers if 1 <= number <= len(source_records)}
                    )
                    if not source_indexes:
                        source_indexes = [0]
                    timeline_event = TimelineEvent(
                        id=uuid.uuid4(),
                        case_id=case.id,
                        date_label=event.date_label,
                        occurred_on=parse_timeline_date(event.date_label),
                        occurred_time=parse_timeline_time(event.date_label),
                        title=event.title,
                        description=event.description,
                        confidence=event.confidence,
                        source_note="Supported by " + ", ".join(f"[{index + 1}]" for index in source_indexes),
                    )
                    db.add(timeline_event)
                    for index in source_indexes:
                        db.add(
                            TimelineEventSource(
                                timeline_event_id=timeline_event.id,
                                source_id=source_records[index].id,
                            )
                        )
                await db.execute(
                    delete(PersonRelationship).where(
                        PersonRelationship.case_id == case.id,
                        PersonRelationship.ai_suggested.is_(True),
                    )
                )
                await db.execute(delete(Person).where(Person.case_id == case.id, Person.ai_suggested.is_(True)))
                entity_records: dict[str, Person] = {}
                for entity in draft.entities:
                    entity_id = uuid.uuid4()
                    person = Person(
                        id=entity_id,
                        case_id=case.id,
                        name=entity.name,
                        slug=_slug(entity.name, str(entity_id)[:8]),
                        role=entity.role,
                        category=entity.category,
                        entity_type=entity.entity_type,
                        relationship_to_primary=entity.relationship_to_primary,
                        summary=entity.summary,
                        is_primary=entity.is_primary,
                        ai_suggested=True,
                        review_status="suggested",
                    )
                    db.add(person)
                    entity_records[entity.name.casefold()] = person
                await db.flush()
                seen_relationships: set[tuple[uuid.UUID, uuid.UUID, str]] = set()
                for relationship in draft.relationships:
                    source_person = entity_records.get(relationship.source_name.casefold())
                    target_person = entity_records.get(relationship.target_name.casefold())
                    source_indexes = sorted(
                        {number - 1 for number in relationship.source_numbers if 1 <= number <= len(source_records)}
                    )
                    if (
                        source_person is None
                        or target_person is None
                        or source_person.id == target_person.id
                        or not source_indexes
                    ):
                        continue
                    relationship_key = (
                        source_person.id,
                        target_person.id,
                        relationship.relationship_type.casefold(),
                    )
                    if relationship_key in seen_relationships:
                        continue
                    seen_relationships.add(relationship_key)
                    supporting_source = source_records[source_indexes[0]]
                    db.add(
                        PersonRelationship(
                            case_id=case.id,
                            source_person_id=source_person.id,
                            target_person_id=target_person.id,
                            relationship_type=relationship.relationship_type[:50],
                            label=relationship.label[:100],
                            description=relationship.description,
                            confidence=relationship.confidence,
                            source_type=supporting_source.source_type,
                            source_id=supporting_source.id,
                            source_url=supporting_source.url,
                            ai_suggested=True,
                            review_status="suggested",
                        )
                    )
                await db.execute(
                    delete(CaseLocation).where(
                        CaseLocation.case_id == case.id,
                        CaseLocation.ai_suggested.is_(True),
                    )
                )
                for location in draft.locations:
                    source_indexes = sorted(
                        {number - 1 for number in location.source_numbers if 1 <= number <= len(source_records)}
                    )
                    if not source_indexes:
                        continue
                    supporting_source = source_records[source_indexes[0]]
                    db.add(
                        CaseLocation(
                            case_id=case.id,
                            name=location.name[:240],
                            description=location.description,
                            latitude=location.latitude,
                            longitude=location.longitude,
                            location_type=location.location_type,
                            occurred_on=location.occurred_on,
                            precision=location.precision,
                            verification_status="source_backed",
                            source_id=supporting_source.id,
                            source_url=supporting_source.url,
                            ai_suggested=True,
                            review_status="suggested",
                        )
                    )
                for prompt in draft.discussion_prompts[:3]:
                    source_indexes = sorted(
                        {number - 1 for number in prompt.source_numbers if 1 <= number <= len(source_records)}
                    )
                    if not source_indexes:
                        continue
                    thread = DiscussionThread(
                        id=uuid.uuid4(),
                        case_id=case.id,
                        title=prompt.title,
                        body=prompt.body,
                        thread_type=prompt.thread_type,
                        created_by_user_id=case.created_by_user_id,
                        ai_generated=True,
                        review_status="suggested",
                    )
                    db.add(thread)
                    for index in source_indexes:
                        db.add(
                            DiscussionThreadSource(
                                thread_id=thread.id,
                                source_id=source_records[index].id,
                            )
                        )
                seen_evidence_sources: set[int] = set()
                for suggestion in draft.evidence_links[:3]:
                    source_index = suggestion.source_number - 1
                    if source_index < 0 or source_index >= len(source_records):
                        continue
                    if source_index in seen_evidence_sources:
                        continue
                    seen_evidence_sources.add(source_index)
                    supporting_source = source_records[source_index]
                    db.add(
                        Evidence(
                            case_id=case.id,
                            uploaded_by_user_id=case.created_by_user_id,
                            title=suggestion.title,
                            description=suggestion.description,
                            evidence_type=suggestion.evidence_type,
                            source_id=supporting_source.id,
                            source_url=supporting_source.url,
                            verification_status="source_backed",
                            processing_status="available",
                            ai_generated=True,
                            review_status="suggested",
                        )
                    )
                case.ai_research_status = "generating_banner"
                await db.commit()
                previous_cover_key = case.cover_image_object_key
                case.cover_image_object_key = await generator.generate_banner(
                    str(case.id), draft.banner_prompt
                )
                case.cover_image_url = f"/api/v1/cases/{case.id}/cover"
                await _complete_generation(db, case, job)
                if previous_cover_key and previous_cover_key != case.cover_image_object_key:
                    try:
                        await storage.delete(previous_cover_key)
                    except Exception:
                        pass
            except Exception as exc:
                await db.rollback()
                case = await db.scalar(select(Case).where(Case.id == case_id))
                job = await db.scalar(select(CaseGenerationJob).where(CaseGenerationJob.id == job_id))
                message = str(exc)[:500]
                if case is not None:
                    case.ai_research_status = "failed"
                    case.ai_error_message = message
                if job is not None:
                    job.status = "failed"
                    job.error_message = message
                    job.completed_at = utc_now()
                await db.commit()
                raise
    finally:
        await engine.dispose()


def _publisher(url: str) -> str:
    hostname = (urlsplit(url).hostname or "Unknown publisher").removeprefix("www.")
    return hostname


def _source_type(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").lower()
    if hostname.endswith(".gov"):
        return "government"
    if "court" in hostname:
        return "court_record"
    if any(marker in hostname for marker in ("police", "sheriff", "fbi.gov")):
        return "official"
    return "news"
