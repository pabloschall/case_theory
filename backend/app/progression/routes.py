from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.db.session import get_db
from app.progression.schemas import (
    LedgerPage,
    ProgressionAcknowledge,
    ProgressionPrivacyUpdate,
    ProgressionSummary,
)
from app.progression.service import ProgressionService
from app.users.models import User

router = APIRouter(prefix="/users/me/progression", tags=["progression"])


@router.get("", response_model=ProgressionSummary)
async def progression_summary(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProgressionSummary:
    return await ProgressionService(db).summary(user.id)


@router.get("/ledger", response_model=LedgerPage)
async def progression_ledger(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LedgerPage:
    return await ProgressionService(db).ledger(user.id, page, page_size)


@router.patch("/acknowledge", status_code=204, dependencies=[Depends(verify_csrf)])
async def acknowledge_progression(
    data: ProgressionAcknowledge,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ProgressionService(db).acknowledge(user.id, data.receipt_ids, data.badge_codes)


@router.patch("/privacy", status_code=204, dependencies=[Depends(verify_csrf)])
async def update_progression_privacy(
    data: ProgressionPrivacyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ProgressionService(db).update_privacy(user.id, data.show_rank, data.show_badges)
