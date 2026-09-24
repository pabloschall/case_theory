import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cases.models import Case, CaseGenerationJob, CaseSource
from app.common.timestamps import utc_now
from app.config.settings import get_settings
from app.db import models as _models  # noqa: F401
from app.integrations.fbi.enrichment import FBIEnrichmentService, OpenAIFBISourceEnricher
from app.workers.celery_app import celery_app


@celery_app.task(name="fbi.enrich_case", bind=True, max_retries=2)  # type: ignore[untyped-decorator]
def enrich_fbi_case(self: object, case_id: str, job_id: str) -> None:
    asyncio.run(_enrich_fbi_case(uuid.UUID(case_id), uuid.UUID(job_id)))


async def _enrich_fbi_case(case_id: uuid.UUID, job_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            case = await db.get(Case, case_id)
            job = await db.get(CaseGenerationJob, job_id)
            source = await db.scalar(
                select(CaseSource).where(
                    CaseSource.case_id == case_id, CaseSource.source_type == "fbi"
                )
            )
            if case is None or job is None or source is None:
                return
            enricher = OpenAIFBISourceEnricher(settings)
            case.ai_research_status = "enriching_official_source"
            job.status = "running"
            job.started_at = utc_now()
            job.text_model = enricher.model_name
            await db.commit()
            try:
                draft = await enricher.enrich(source.source_payload)
                await FBIEnrichmentService(db).apply(
                    case_id, source, draft, model_name=enricher.model_name
                )
                job = await db.get(CaseGenerationJob, job_id)
                if job:
                    job.status = "complete"
                    job.completed_at = utc_now()
                    await db.commit()
            except Exception as exc:
                await db.rollback()
                case = await db.get(Case, case_id)
                job = await db.get(CaseGenerationJob, job_id)
                message = str(exc)[:500]
                if case:
                    case.ai_research_status = "failed"
                    case.ai_error_message = message
                if job:
                    job.status = "failed"
                    job.error_message = message
                    job.completed_at = utc_now()
                await db.commit()
                raise
    finally:
        await engine.dispose()
