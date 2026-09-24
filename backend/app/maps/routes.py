import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_optional_current_user, verify_csrf
from app.cases.dependencies import require_public_case_access
from app.db.session import get_db
from app.maps.schemas import LocationCreate, LocationPatch, LocationRead
from app.maps.service import LocationService
from app.subscriptions.dependencies import require_permission
from app.subscriptions.permissions import PermissionService
from app.users.models import User

router = APIRouter(
    prefix="/cases/{case_id}/locations",
    tags=["locations"],
    dependencies=[Depends(require_public_case_access)],
)


@router.get("", response_model=list[LocationRead])
async def list_locations(
    case_id: uuid.UUID,
    user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LocationRead]:
    include_evidence = (
        await PermissionService(db).allows(
            user.id, "evidence.read", is_admin=user.is_admin
        )
        if user is not None
        else False
    )
    return await LocationService(db).list(
        case_id, include_evidence_details=include_evidence
    )


@router.post(
    "",
    response_model=LocationRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("map.write"))],
)
async def create_location(
    case_id: uuid.UUID,
    data: LocationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationRead:
    return await LocationService(db).create(case_id, data, user.id)


@router.patch(
    "/{location_id}",
    response_model=LocationRead,
    dependencies=[Depends(verify_csrf), Depends(require_permission("map.write"))],
)
async def update_location(
    case_id: uuid.UUID,
    location_id: uuid.UUID,
    data: LocationPatch,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationRead:
    return await LocationService(db).update(case_id, location_id, data)


@router.delete(
    "/{location_id}",
    status_code=204,
    dependencies=[Depends(verify_csrf), Depends(require_permission("map.write"))],
)
async def delete_location(
    case_id: uuid.UUID,
    location_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await LocationService(db).delete(case_id, location_id)
    return Response(status_code=204)
