import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, verify_csrf
from app.db.session import get_db
from app.moderation.schemas import (
    ModerationDecisionRequest,
    ReportCreate,
    ReportPage,
    ReportRead,
)
from app.moderation.service import ModerationService
from app.users.models import User

router = APIRouter(tags=["moderation"])


@router.post(
    "/reports",
    response_model=ReportRead,
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
async def create_report(
    data: ReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportRead:
    return await ModerationService(db).create_report(user, data)


@router.get(
    "/admin/reports",
    response_model=ReportPage,
    dependencies=[Depends(require_admin)],
)
async def list_reports(
    status: str | None = Query(default="pending", max_length=30),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportPage:
    items, total = await ModerationService(db).reports(status, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return ReportPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.patch(
    "/admin/reports/{report_id}",
    response_model=ReportRead,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
async def decide_report(
    report_id: uuid.UUID,
    data: ModerationDecisionRequest,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportRead:
    return await ModerationService(db).decide(report_id, data, actor)
