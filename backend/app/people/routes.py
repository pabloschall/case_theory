import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.cases.dependencies import require_public_case_access
from app.db.session import get_db
from app.evidence.schemas import EvidenceLinkRequest, EvidenceRead
from app.people.schemas import (
    PersonCreate,
    PersonNoteCreate,
    PersonNoteRead,
    PersonPatch,
    PersonRead,
    RelationshipCreate,
    RelationshipPatch,
    RelationshipRead,
)
from app.people.service import PeopleService
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(
    prefix="/cases/{case_id}",
    tags=["people"],
    dependencies=[Depends(require_public_case_access)],
)


@router.get("/people", response_model=list[PersonRead])
async def list_people(
    case_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[PersonRead]:
    return await PeopleService(db).list_people(case_id)


@router.get("/relationships", response_model=list[RelationshipRead])
async def list_relationships(
    case_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[RelationshipRead]:
    return await PeopleService(db).list_relationships(case_id)


@router.get("/people/{person_id}", response_model=PersonRead)
async def get_person(
    case_id: uuid.UUID, person_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> PersonRead:
    return await PeopleService(db).get_person(case_id, person_id)


@router.post(
    "/people",
    response_model=PersonRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def create_person(
    case_id: uuid.UUID, data: PersonCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PersonRead:
    return await PeopleService(db).create_person(case_id, data, user.id)


@router.patch(
    "/people/{person_id}",
    response_model=PersonRead,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def update_person(
    case_id: uuid.UUID,
    person_id: uuid.UUID,
    data: PersonPatch,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PersonRead:
    return await PeopleService(db).update_person(case_id, person_id, data)


@router.post(
    "/relationships",
    response_model=RelationshipRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def create_relationship(
    case_id: uuid.UUID,
    data: RelationshipCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RelationshipRead:
    return await PeopleService(db).create_relationship(case_id, data, user.id)


@router.patch(
    "/relationships/{relationship_id}",
    response_model=RelationshipRead,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def update_relationship(
    case_id: uuid.UUID,
    relationship_id: uuid.UUID,
    data: RelationshipPatch,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RelationshipRead:
    return await PeopleService(db).update_relationship(case_id, relationship_id, data)


@router.delete(
    "/relationships/{relationship_id}",
    status_code=204,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def delete_relationship(
    case_id: uuid.UUID,
    relationship_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await PeopleService(db).delete_relationship(case_id, relationship_id)
    return Response(status_code=204)


@router.get("/people/{person_id}/evidence", response_model=list[EvidenceRead])
async def person_evidence(
    case_id: uuid.UUID, person_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[EvidenceRead]:
    return await PeopleService(db).evidence(case_id, person_id)


@router.post(
    "/people/{person_id}/evidence",
    status_code=204,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def attach_person_evidence(
    case_id: uuid.UUID,
    person_id: uuid.UUID,
    data: EvidenceLinkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await PeopleService(db).attach_evidence(case_id, person_id, data.evidence_id, user.id)


@router.get("/people/{person_id}/notes", response_model=list[PersonNoteRead])
async def person_notes(
    case_id: uuid.UUID, person_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[PersonNoteRead]:
    return await PeopleService(db).notes(case_id, person_id)


@router.post(
    "/people/{person_id}/notes",
    response_model=PersonNoteRead,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def create_person_note(
    case_id: uuid.UUID,
    person_id: uuid.UUID,
    data: PersonNoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PersonNoteRead:
    return await PeopleService(db).create_note(case_id, person_id, data, user)


@router.patch(
    "/people/{person_id}/notes/{note_id}",
    response_model=PersonNoteRead,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def update_person_note(
    case_id: uuid.UUID,
    person_id: uuid.UUID,
    note_id: uuid.UUID,
    data: PersonNoteCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PersonNoteRead:
    return await PeopleService(db).update_note(case_id, person_id, note_id, data)


@router.delete(
    "/people/{person_id}/notes/{note_id}",
    status_code=204,
    dependencies=[Depends(verify_csrf), Depends(require_permission("people.write"))],
)
async def delete_person_note(
    case_id: uuid.UUID,
    person_id: uuid.UUID,
    note_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await PeopleService(db).delete_note(case_id, person_id, note_id)
    return Response(status_code=204)
