import uuid

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_optional_current_user
from app.cases.models import Case, CaseMember
from app.common.errors import AppError
from app.db.session import get_db
from app.users.models import User


async def require_case_access(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    membership = select(CaseMember.id).where(
        CaseMember.case_id == Case.id,
        CaseMember.user_id == user.id,
    ).exists()
    conditions = [Case.privacy == "public", Case.created_by_user_id == user.id, membership]
    if user.is_admin:
        conditions.append(Case.id == case_id)
    case_exists = await db.scalar(
        select(Case.id).where(Case.id == case_id, or_(*conditions))
    )
    if case_exists is None:
        raise AppError(404, "case_not_found", "Case was not found")


async def require_public_case_access(
    case_id: uuid.UUID,
    user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conditions = [Case.privacy == "public"]
    if user is not None:
        conditions.append(Case.created_by_user_id == user.id)
        conditions.append(
            select(CaseMember.id).where(
                CaseMember.case_id == Case.id,
                CaseMember.user_id == user.id,
            ).exists()
        )
        if user.is_admin:
            conditions.append(Case.id == case_id)
    case_exists = await db.scalar(
        select(Case.id).where(Case.id == case_id, or_(*conditions))
    )
    if case_exists is None:
        raise AppError(404, "case_not_found", "Case was not found")
