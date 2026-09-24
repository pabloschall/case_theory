from collections.abc import Awaitable, Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.subscriptions.permissions import PermissionService
from app.users.models import User

PermissionDependency = Callable[..., Awaitable[None]]


def require_permission(
    permission: str,
    *,
    required_tier: int = 2,
    message: str = "Upgrade your plan to use this feature",
) -> PermissionDependency:
    async def dependency(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        await PermissionService(db).require(
            user,
            permission,
            required_tier=required_tier,
            message=message,
        )

    return dependency
