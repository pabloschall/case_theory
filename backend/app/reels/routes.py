import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.cases.dependencies import require_case_access
from app.db.session import get_db
from app.reels.schemas import ReelDraftCreate, ReelDraftRead, ReelDraftUpdate
from app.reels.service import ReelService
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(prefix="/cases/{case_id}/reels", tags=["reels"])


@router.get(
    "",
    response_model=list[ReelDraftRead],
    dependencies=[Depends(require_case_access), Depends(require_permission("ai.research", required_tier=2))],
)
async def list_reels(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[ReelDraftRead]:
    return await ReelService(db).list(case_id)


@router.post(
    "",
    response_model=ReelDraftRead,
    status_code=201,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("ai.research", required_tier=2)),
    ],
)
async def create_reel(
    case_id: uuid.UUID,
    data: ReelDraftCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReelDraftRead:
    return await ReelService(db).create(case_id, user, data)


@router.patch(
    "/{reel_id}",
    response_model=ReelDraftRead,
    dependencies=[
        Depends(verify_csrf),
        Depends(require_case_access),
        Depends(require_permission("ai.research", required_tier=2)),
    ],
)
async def update_reel(
    case_id: uuid.UUID,
    reel_id: uuid.UUID,
    data: ReelDraftUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReelDraftRead:
    return await ReelService(db).update(case_id, reel_id, user, data)
