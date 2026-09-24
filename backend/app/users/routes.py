import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.auth.dependencies import get_current_user, verify_csrf
from app.db.session import get_db
from app.messaging.schemas import MemberRead
from app.messaging.service import MessagingService
from app.storage.base import StorageProvider
from app.storage.provider import get_storage_provider
from app.subscriptions.permissions import PermissionService
from app.users.models import User
from app.users.schemas import (
    AvatarUploadRequest,
    AvatarUploadTicket,
    BlockState,
    CurrentUser,
    ProfileUpdate,
)
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


async def current_user_read(user: User, db: AsyncSession) -> CurrentUser:
    service = PermissionService(db)
    context = await service.for_user(user.id, is_admin=user.is_admin)
    allowance = await service.case_allowance(user)
    return CurrentUser(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.profile.display_name,
        bio=user.profile.bio,
        avatar_url=user.profile.avatar_url,
        is_verified=user.is_verified,
        plan_code=context.plan_code,
        tier_level=context.tier_level,
        permissions=sorted(context.permissions),
        ai_cases_remaining=allowance.remaining,
        ai_limit_period=allowance.period,
        ai_resets_at=allowance.resets_at,
        weekly_cases_remaining=allowance.remaining,
        weekly_case_limit=context.weekly_case_limit,
        weekly_cases_reset_at=allowance.resets_at,
        created_at=user.created_at,
    )


@router.get("/me", response_model=CurrentUser)
async def current_user(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    return await current_user_read(user, db)


@router.patch("/me", response_model=CurrentUser, dependencies=[Depends(verify_csrf)])
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    updated = await UserService(db).update_profile(user, data)
    return await current_user_read(updated, db)


@router.post(
    "/me/avatar",
    response_model=AvatarUploadTicket,
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
async def request_avatar_upload(
    data: AvatarUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> AvatarUploadTicket:
    return await UserService(db, storage).request_avatar(user, data)


@router.post(
    "/me/avatar/{upload_id}/complete",
    response_model=CurrentUser,
    dependencies=[Depends(verify_csrf)],
)
async def complete_avatar_upload(
    upload_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> CurrentUser:
    updated = await UserService(db, storage).complete_avatar(user, upload_id)
    return await current_user_read(updated, db)


@router.get("/me/blocked", response_model=list[MemberRead])
async def blocked_users(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[MemberRead]:
    return [
        MemberRead(
            id=item.id,
            username=item.username,
            display_name=item.profile.display_name,
            bio=item.profile.bio,
            avatar_url=item.profile.avatar_url,
            is_blocked_by_me=True,
        )
        for item in await UserService(db).blocked_users(user)
    ]


@router.post(
    "/{user_id}/block",
    response_model=BlockState,
    dependencies=[Depends(verify_csrf)],
)
async def block_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlockState:
    await UserService(db).block(user, user_id)
    return BlockState(is_blocked=True)


@router.delete(
    "/{user_id}/block",
    response_model=BlockState,
    dependencies=[Depends(verify_csrf)],
)
async def unblock_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlockState:
    await UserService(db).unblock(user, user_id)
    return BlockState(is_blocked=False)


@router.get("/{user_id}/avatar", response_class=RedirectResponse)
async def user_avatar(
    user_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> RedirectResponse:
    object_key = await UserService(db).avatar_object_key(user_id)
    return RedirectResponse(await storage.create_download_url(object_key), status_code=307)


@router.get("/{user_id}", response_model=MemberRead)
async def member_profile(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberRead:
    return await MessagingService(db).profile(user_id, user)
