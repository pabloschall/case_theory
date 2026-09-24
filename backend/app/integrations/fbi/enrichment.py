import json
import uuid
from datetime import date
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cases.models import (
    Case,
    CaseGenerationJob,
    CaseSource,
    CaseSummary,
    Source,
    SourceCitation,
    TimelineEvent,
    TimelineEventSource,
)
from app.common.errors import AppError
from app.config.settings import Settings
from app.evidence.models import Evidence
from app.people.models import Person
from app.people.service import _slug
from app.subscriptions.permissions import PermissionService
from app.users.models import User


class FBIEnrichedSummary(BaseModel):
    body: str = Field(min_length=20, max_length=12000)
    source_fields: list[str] = Field(min_length=1, max_length=8)


class FBIEnrichedEvent(BaseModel):
    date_label: str
    occurred_on: date | None = None
    date_precision: str = Field(pattern="^(exact|month|year|approximate|unknown)$")
    title: str
    description: str
    confidence: str = Field(pattern="^(low|medium|high)$")
    source_field: str
    source_text: str


class FBIEnrichedPerson(BaseModel):
    name: str
    role: str
    summary: str
    source_field: str
    source_text: str


class FBIEnrichedEvidence(BaseModel):
    title: str
    description: str
    evidence_type: str = Field(
        pattern="^(vehicle|clothing|physical_evidence|location|document|photograph|weapon|personal_item|other)$"
    )
    source_field: str
    source_text: str


class FBIEnrichmentDraft(BaseModel):
    summary: FBIEnrichedSummary
    timeline: list[FBIEnrichedEvent] = Field(default_factory=list, max_length=15)
    people: list[FBIEnrichedPerson] = Field(default_factory=list, max_length=20)
    evidence: list[FBIEnrichedEvidence] = Field(default_factory=list, max_length=20)


class FBISourceEnricher(Protocol):
    @property
    def model_name(self) -> str: ...

    async def enrich(self, payload: dict[str, object]) -> FBIEnrichmentDraft: ...


class OpenAIFBISourceEnricher:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model_name = settings.ai_text_model

    @property
    def model_name(self) -> str:
        return self._model_name

    async def enrich(self, payload: dict[str, object]) -> FBIEnrichmentDraft:
        response = await self.client.responses.parse(
            model=self.model_name,
            instructions=(
                "Create reviewable case suggestions using only the supplied official FBI JSON. Never invent a "
                "person, suspect, motive, relationship, item, place, or date. Preserve uncertainty. Exact dates may "
                "only be used when explicit in the source; otherwise select month, year, approximate, or unknown. "
                "Every suggested event, person, and evidence item must name one exact top-level JSON source_field "
                "and include a short supporting source_text excerpt. Do not treat an FBI publication date as a case "
                "event. The summary must be neutral and distinguish official statements from open questions."
            ),
            input=json.dumps(payload, ensure_ascii=False)[:80_000],
            text_format=FBIEnrichmentDraft,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no FBI enrichment draft")
        return response.output_parsed


class FBIEnrichmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def queue(self, case_id: uuid.UUID, user: User) -> CaseGenerationJob:
        if not await PermissionService(self.db).allows(
            user.id, "ai.research", is_admin=user.is_admin
        ):
            raise AppError(403, "ai_research_forbidden", "Your account cannot run AI enrichment")
        case = await self.db.get(Case, case_id)
        if case is None or (case.created_by_user_id != user.id and not user.is_admin):
            raise AppError(404, "case_not_found", "Case was not found")
        source = await self.db.scalar(
            select(CaseSource).where(
                CaseSource.case_id == case_id, CaseSource.source_type == "fbi"
            )
        )
        if source is None:
            raise AppError(409, "fbi_source_missing", "This case was not imported from the FBI")
        job = CaseGenerationJob(case_id=case_id, status="queued")
        case.ai_research_status = "queued_source_enrichment"
        self.db.add(job)
        await self.db.commit()
        return job

    async def apply(
        self,
        case_id: uuid.UUID,
        source: CaseSource,
        draft: FBIEnrichmentDraft,
        *,
        model_name: str,
    ) -> None:
        case = await self.db.get(Case, case_id)
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        official_source = await self.db.scalar(
            select(Source).where(Source.case_id == case_id, Source.source_type == "official")
        )
        if official_source is None:
            raise AppError(409, "fbi_source_missing", "Official source reference is missing")
        await self.db.execute(
            update(CaseSummary).where(CaseSummary.case_id == case_id).values(is_current=False)
        )
        version = (
            await self.db.scalar(
                select(func.max(CaseSummary.version)).where(CaseSummary.case_id == case_id)
            )
        ) or 0
        summary_id = uuid.uuid4()
        self.db.add(
            CaseSummary(
                id=summary_id,
                case_id=case_id,
                version=version + 1,
                body=draft.summary.body,
                source="ai",
                ai_model=model_name,
                is_current=True,
            )
        )
        for field in draft.summary.source_fields:
            self._cite(source.id, "summary", summary_id, field, None)
        for event_suggestion in draft.timeline:
            event_id = uuid.uuid4()
            self.db.add(
                TimelineEvent(
                    id=event_id,
                    case_id=case_id,
                    date_label=event_suggestion.date_label,
                    occurred_on=event_suggestion.occurred_on,
                    date_precision=event_suggestion.date_precision,
                    title=event_suggestion.title,
                    description=event_suggestion.description,
                    verification_status="ai_suggested",
                    confidence=event_suggestion.confidence,
                    source_note="AI-extracted from the official FBI source; requires review.",
                    ai_generated=True,
                )
            )
            self.db.add(TimelineEventSource(timeline_event_id=event_id, source_id=official_source.id))
            self._cite(
                source.id,
                "timeline_event",
                event_id,
                event_suggestion.source_field,
                event_suggestion.source_text,
            )
        for person_suggestion in draft.people:
            person_id = uuid.uuid4()
            self.db.add(
                Person(
                    id=person_id,
                    case_id=case_id,
                    name=person_suggestion.name,
                    slug=_slug(person_suggestion.name, str(person_id)[:8]),
                    role=person_suggestion.role[:120],
                    category="other",
                    entity_type="person",
                    summary=person_suggestion.summary,
                    ai_suggested=True,
                    review_status="suggested",
                )
            )
            self._cite(
                source.id,
                "person",
                person_id,
                person_suggestion.source_field,
                person_suggestion.source_text,
            )
        for evidence_suggestion in draft.evidence:
            evidence_id = uuid.uuid4()
            self.db.add(
                Evidence(
                    id=evidence_id,
                    case_id=case_id,
                    uploaded_by_user_id=case.created_by_user_id,
                    title=evidence_suggestion.title,
                    description=evidence_suggestion.description,
                    evidence_type=(
                        "other"
                        if evidence_suggestion.evidence_type == "physical_evidence"
                        else evidence_suggestion.evidence_type
                    ),
                    source_url=source.source_url,
                    source_id=official_source.id,
                    verification_status="source_backed",
                    processing_status="available",
                    ai_generated=True,
                    review_status="suggested",
                )
            )
            self._cite(
                source.id,
                "evidence",
                evidence_id,
                evidence_suggestion.source_field,
                evidence_suggestion.source_text,
            )
        case.ai_research_status = "complete"
        await self.db.commit()

    def _cite(
        self,
        source_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        source_field: str,
        source_text: str | None,
    ) -> None:
        self.db.add(
            SourceCitation(
                case_source_id=source_id,
                resource_type=resource_type,
                resource_id=resource_id,
                source_field=source_field,
                source_text=source_text,
                interpretation_type="ai_extracted",
            )
        )
