import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.cases.dependencies import require_case_access
from app.db.session import get_db
from app.notes.schemas import (
    NotebookNotePage,
    NotebookNoteRead,
    NotebookNoteWrite,
    TimelineEntryRead,
    TimelineEntryWrite,
)
from app.notes.service import NotebookService
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(prefix="/cases/{case_id}", tags=["case-contributions"])


@router.get(
    "/notes",
    response_model=NotebookNotePage,
    dependencies=[Depends(require_case_access)],
)
async def list_notes(
    case_id: uuid.UUID,
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotebookNotePage:
    return await NotebookService(db).list_notes(
        case_id, user, cursor=cursor, limit=limit
    )


@router.post(
    "/notes",
    response_model=NotebookNoteRead,
    status_code=201,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(
            require_permission(
                "notes.write",
                required_tier=2,
                message="Creating case notes requires a paid plan",
            )
        ),
    ],
)
async def create_note(
    case_id: uuid.UUID,
    data: NotebookNoteWrite,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotebookNoteRead:
    return await NotebookService(db).create_note(case_id, user, data)


@router.patch(
    "/notes/{note_id}",
    response_model=NotebookNoteRead,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("notes.write", required_tier=2)),
    ],
)
async def update_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    data: NotebookNoteWrite,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotebookNoteRead:
    return await NotebookService(db).update_note(case_id, note_id, user, data)


@router.delete(
    "/notes/{note_id}",
    status_code=204,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("notes.write", required_tier=2)),
    ],
)
async def delete_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await NotebookService(db).delete_note(case_id, note_id, user.id)
    return Response(status_code=204)


@router.get(
    "/my-timeline",
    response_model=list[TimelineEntryRead],
    dependencies=[Depends(require_case_access)],
)
async def list_timeline_entries(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimelineEntryRead]:
    return await NotebookService(db).list_timeline(case_id, user)


@router.post(
    "/my-timeline",
    response_model=TimelineEntryRead,
    status_code=201,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(
            require_permission(
                "timeline.private_write",
                required_tier=2,
                message="Creating timeline entries requires a paid plan",
            )
        ),
    ],
)
async def create_timeline_entry(
    case_id: uuid.UUID,
    data: TimelineEntryWrite,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineEntryRead:
    return await NotebookService(db).create_timeline_entry(case_id, user, data)


@router.patch(
    "/my-timeline/{entry_id}",
    response_model=TimelineEntryRead,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("timeline.private_write", required_tier=2)),
    ],
)
async def update_timeline_entry(
    case_id: uuid.UUID,
    entry_id: uuid.UUID,
    data: TimelineEntryWrite,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineEntryRead:
    return await NotebookService(db).update_timeline_entry(case_id, entry_id, user, data)


@router.delete(
    "/my-timeline/{entry_id}",
    status_code=204,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("timeline.private_write", required_tier=2)),
    ],
)
async def delete_timeline_entry(
    case_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await NotebookService(db).delete_timeline_entry(case_id, entry_id, user.id)
    return Response(status_code=204)
