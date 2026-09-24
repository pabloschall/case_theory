import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_optional_current_user, verify_csrf
from app.cases.dependencies import require_public_case_access
from app.db.session import get_db
from app.discussions.schemas import (
    CommentCreate,
    ReactionToggle,
    ThreadCreate,
    ThreadPage,
    ThreadRead,
    ThreadVoteRead,
)
from app.discussions.service import DiscussionService
from app.subscriptions.dependencies import require_permission
from app.subscriptions.permissions import PermissionService
from app.users.models import User

router = APIRouter(
    prefix="/cases/{case_id}/discussions",
    tags=["discussions"],
    dependencies=[Depends(require_public_case_access)],
)


@router.get("", response_model=ThreadPage)
async def list_threads(
    case_id: uuid.UUID,
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadPage:
    include_evidence = (
        await PermissionService(db).allows(
            user.id, "evidence.read", is_admin=user.is_admin
        )
        if user is not None
        else False
    )
    (
        items,
        next_cursor,
        has_more,
        total,
        active_count,
        source_link_count,
        comment_count,
    ) = await DiscussionService(db).list_threads(
        case_id,
        user.id if user is not None else None,
        cursor=cursor,
        limit=limit,
        include_evidence_details=include_evidence,
    )
    return ThreadPage(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total=total,
        active_count=active_count,
        source_link_count=source_link_count,
        comment_count=comment_count,
    )


@router.post(
    "",
    response_model=ThreadRead,
    status_code=201,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_permission("discussion.write", required_tier=2)),
    ],
)
async def create_thread(
    case_id: uuid.UUID,
    data: ThreadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadRead:
    return await DiscussionService(db).create_thread(case_id, user, data)


@router.post(
    "/{thread_id}/vote",
    response_model=ThreadVoteRead,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_permission("discussion.write", required_tier=2)),
    ],
)
async def toggle_thread_vote(
    case_id: uuid.UUID,
    thread_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadVoteRead:
    return await DiscussionService(db).toggle_vote(case_id, thread_id, user.id)


@router.post(
    "/{thread_id}/comments",
    response_model=ThreadRead,
    status_code=201,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_permission("discussion.write", required_tier=2)),
    ],
)
async def add_comment(
    case_id: uuid.UUID,
    thread_id: uuid.UUID,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadRead:
    return await DiscussionService(db).add_comment(case_id, thread_id, user, data)


@router.post(
    "/{thread_id}/comments/{comment_id}/reactions",
    response_model=ThreadRead,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_permission("discussion.write", required_tier=2)),
    ],
)
async def toggle_reaction(
    case_id: uuid.UUID,
    thread_id: uuid.UUID,
    comment_id: uuid.UUID,
    data: ReactionToggle,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadRead:
    return await DiscussionService(db).toggle_reaction(case_id, thread_id, comment_id, user.id, data)
