import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_optional_current_user, verify_csrf
from app.cases.dependencies import require_public_case_access
from app.db.session import get_db
from app.evidence.schemas import (
    EvidenceCommentCreate,
    EvidenceCommentPage,
    EvidenceCommentRead,
    EvidenceLinkRequest,
    EvidencePage,
    EvidenceRead,
    EvidenceUrl,
    ExternalEvidenceCreate,
    UploadRequest,
    UploadTicket,
)
from app.evidence.service import EvidenceService
from app.storage.base import StorageProvider
from app.storage.provider import get_storage_provider
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(
    prefix="/cases/{case_id}/evidence",
    tags=["evidence"],
    dependencies=[Depends(require_public_case_access)],
)


@router.get("", response_model=EvidencePage)
async def list_evidence(
    case_id: uuid.UUID,
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> EvidencePage:
    include_details = True
    items, next_cursor, has_more, total = await EvidenceService(db, storage).list(
        case_id,
        cursor=cursor,
        limit=limit,
        include_details=include_details,
    )
    return EvidencePage(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total=total,
    )


@router.get("/{evidence_id}/comments", response_model=EvidenceCommentPage)
async def list_evidence_comments(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> EvidenceCommentPage:
    items, next_cursor, has_more, total = await EvidenceService(db, storage).list_comments(
        case_id,
        evidence_id,
        user,
        cursor=cursor,
        limit=limit,
    )
    return EvidenceCommentPage(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total=total,
    )


@router.post(
    "/{evidence_id}/comments",
    response_model=EvidenceCommentRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("discussion.write"))],
)
async def create_evidence_comment(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    data: EvidenceCommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> EvidenceCommentRead:
    return await EvidenceService(db, storage).create_comment(case_id, evidence_id, user, data)


@router.delete(
    "/{evidence_id}/comments/{comment_id}",
    status_code=204,
    dependencies=[Depends(verify_csrf), Depends(require_permission("discussion.write"))],
)
async def delete_evidence_comment(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    comment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> None:
    await EvidenceService(db, storage).delete_comment(case_id, evidence_id, comment_id, user)


@router.post(
    "/links",
    response_model=EvidenceRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("evidence.upload"))],
)
async def create_external_evidence(
    case_id: uuid.UUID,
    data: ExternalEvidenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> EvidenceRead:
    return await EvidenceService(db, storage).create_external(case_id, user, data)


@router.post(
    "/uploads",
    response_model=UploadTicket,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("evidence.upload"))],
)
async def request_evidence_upload(
    case_id: uuid.UUID,
    data: UploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> UploadTicket:
    return await EvidenceService(db, storage).request_upload(case_id, user, data)


@router.post(
    "/{evidence_id}/complete",
    response_model=EvidenceRead,
    dependencies=[Depends(verify_csrf), Depends(require_permission("evidence.upload"))],
)
async def complete_evidence_upload(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> EvidenceRead:
    return await EvidenceService(db, storage).complete_upload(case_id, evidence_id)


@router.get(
    "/{evidence_id}/url",
    response_model=EvidenceUrl,
)
async def get_evidence_url(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> EvidenceUrl:
    return EvidenceUrl(url=await EvidenceService(db, storage).download_url(case_id, evidence_id))


@router.post(
    "/timeline/{timeline_event_id}",
    status_code=204,
    dependencies=[Depends(verify_csrf), Depends(require_permission("evidence.upload"))],
)
async def attach_evidence_to_timeline(
    case_id: uuid.UUID,
    timeline_event_id: uuid.UUID,
    data: EvidenceLinkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> None:
    await EvidenceService(db, storage).attach_to_timeline(
        case_id, timeline_event_id, data.evidence_id, user.id
    )
