import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.invitations.schemas import (
    InvitationAccepted,
    InvitationCreate,
    InvitationCreated,
    InvitationPreview,
)
from app.invitations.service import InvitationService
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(tags=["invitations"])


@router.post(
    "/cases/{case_id}/invitations",
    response_model=InvitationCreated,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("case.invite"))],
)
async def create_invitation(
    case_id: uuid.UUID,
    data: InvitationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InvitationCreated:
    return await InvitationService(db, settings).create(case_id, user, data.role)


@router.get("/invitations/{token}", response_model=InvitationPreview)
async def preview_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InvitationPreview:
    return await InvitationService(db, settings).preview(token)


@router.post(
    "/invitations/{token}/accept",
    response_model=InvitationAccepted,
    dependencies=[Depends(verify_csrf)],
)
async def accept_invitation(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InvitationAccepted:
    return await InvitationService(db, settings).accept(token, user)
