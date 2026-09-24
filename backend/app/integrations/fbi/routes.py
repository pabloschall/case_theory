import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.cases.models import CaseSource
from app.common.errors import AppError
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.integrations.cache import RedisJSONCache
from app.integrations.fbi.client import FBIClient
from app.integrations.fbi.enrichment import FBIEnrichmentService
from app.integrations.fbi.exceptions import FBIAPIError, FBIAPITimeout, FBICaseNotFound
from app.integrations.fbi.schemas import FBICasePage, FBIImportResult, NormalizedFBICase
from app.integrations.fbi.service import FBICaseImportService
from app.integrations.fbi.tasks import enrich_fbi_case
from app.storage.base import StorageProvider
from app.storage.provider import get_storage_provider
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(
    prefix="/integrations/fbi",
    tags=["FBI case discovery"],
    dependencies=[Depends(require_permission("research.browse", required_tier=2))],
)


def get_fbi_client(
    request: Request, settings: Settings = Depends(get_settings)
) -> FBIClient:
    return FBIClient(settings, cache=RedisJSONCache(request.app.state.redis))


def _translate_error(exc: FBIAPIError) -> AppError:
    if isinstance(exc, FBICaseNotFound):
        return AppError(404, "fbi_case_not_found", "The FBI case was not found")
    if isinstance(exc, FBIAPITimeout):
        return AppError(504, "fbi_api_timeout", "The FBI case service did not respond in time")
    return AppError(503, "fbi_api_unavailable", str(exc))


async def _mark_imported(
    db: AsyncSession, cases: list[NormalizedFBICase]
) -> list[NormalizedFBICase]:
    if not cases:
        return cases
    external_ids = [case.external_id for case in cases]
    rows = await db.execute(
        select(CaseSource.external_id, CaseSource.case_id).where(
            CaseSource.source_type == "fbi", CaseSource.external_id.in_(external_ids)
        )
    )
    imported = {external_id: str(case_id) for external_id, case_id in rows}
    return [
        case.model_copy(
            update={
                "already_imported": case.external_id in imported,
                "imported_case_id": imported.get(case.external_id),
            }
        )
        for case in cases
    ]


@router.get("/cases", response_model=FBICasePage)
async def list_fbi_cases(
    _: Annotated[User, Depends(get_current_user)],
    client: Annotated[FBIClient, Depends(get_fbi_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, le=500),
    q: str | None = Query(default=None, min_length=2, max_length=120),
    field_office: str | None = Query(default=None, max_length=80),
    classification: str | None = Query(default=None, max_length=80),
    status: str | None = Query(default=None, max_length=40),
) -> FBICasePage:
    try:
        result = await client.list_cases(
            page=page,
            title=q,
            field_offices=field_office,
            person_classification=classification,
            status=status,
        )
    except FBIAPIError as exc:
        raise _translate_error(exc) from exc
    return result.model_copy(update={"items": await _mark_imported(db, result.items)})


@router.get("/cases/{external_id}", response_model=NormalizedFBICase)
async def get_fbi_case(
    external_id: str,
    _: Annotated[User, Depends(get_current_user)],
    client: Annotated[FBIClient, Depends(get_fbi_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NormalizedFBICase:
    try:
        normalized = client.normalize(await client.get_case(external_id))
    except FBIAPIError as exc:
        raise _translate_error(exc) from exc
    return (await _mark_imported(db, [normalized]))[0]


@router.post(
    "/cases/{external_id}/import",
    response_model=FBIImportResult,
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
async def import_fbi_case(
    external_id: str,
    user: Annotated[User, Depends(get_current_user)],
    client: Annotated[FBIClient, Depends(get_fbi_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> FBIImportResult:
    try:
        return await FBICaseImportService(db, client, storage).import_case(external_id, user)
    except FBIAPIError as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/imports/{case_id}/enrich",
    status_code=202,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_permission("ai.research", required_tier=3)),
    ],
)
async def enrich_imported_fbi_case(
    case_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    try:
        parsed_case_id = uuid.UUID(case_id)
    except ValueError as exc:
        raise AppError(404, "case_not_found", "Case was not found") from exc
    job = await FBIEnrichmentService(db).queue(parsed_case_id, user)
    enrich_fbi_case.delay(case_id, str(job.id))
    return {"job_id": str(job.id), "status": "queued"}
