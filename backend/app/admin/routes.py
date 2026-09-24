import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    AdminCasePage,
    AdminTierUpdate,
    AdminUserCreate,
    AdminUserPage,
    AdminUserRead,
)
from app.admin.service import AdminService
from app.auth.dependencies import get_current_user, require_admin, verify_csrf
from app.db.session import get_db
from app.storage.base import StorageProvider
from app.storage.provider import get_storage_provider
from app.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
log = structlog.get_logger()


@router.post(
    "/users",
    response_model=AdminUserRead,
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
async def create_admin_user(
    data: AdminUserCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserRead:
    return await AdminService(db).create_admin(data, actor)


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserPage:
    items, total = await AdminService(db).users(q, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminUserPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.patch(
    "/users/{user_id}/tier",
    response_model=AdminUserRead,
    dependencies=[Depends(verify_csrf)],
)
async def update_user_tier(
    user_id: uuid.UUID,
    data: AdminTierUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserRead:
    return await AdminService(db).update_tier(user_id, data.tier_level, actor)


@router.delete("/users/{user_id}", dependencies=[Depends(verify_csrf)])
async def delete_user(
    user_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await AdminService(db).delete_user(user_id, actor)
    return {"message": "User deleted"}


@router.get("/cases", response_model=AdminCasePage)
async def list_cases(
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminCasePage:
    items, total = await AdminService(db).cases(q, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminCasePage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.delete("/cases/{case_id}", dependencies=[Depends(verify_csrf)])
async def delete_case(
    case_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict[str, str]:
    object_keys = await AdminService(db).delete_case(case_id, actor)
    for object_key in object_keys:
        try:
            await storage.delete(object_key)
        except Exception:
            log.warning(
                "case_object_cleanup_failed",
                case_id=str(case_id),
                object_key=object_key,
                exc_info=True,
            )
    return {"message": "Case deleted"}
