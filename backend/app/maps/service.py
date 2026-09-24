import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cases.models import Case, Source
from app.common.errors import AppError
from app.evidence.models import Evidence
from app.evidence.service import to_evidence_read
from app.maps.models import CaseLocation, CaseLocationEvidence, CaseLocationPerson
from app.maps.schemas import (
    LocationCreate,
    LocationPatch,
    LocationRead,
    LocationType,
    Precision,
    ReviewStatus,
    VerificationStatus,
)
from app.people.models import Person
from app.people.service import to_linked_person


class LocationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, case_id: uuid.UUID, *, include_evidence_details: bool = True
    ) -> list[LocationRead]:
        await self._require_case(case_id)
        locations = list(
            (
                await self.db.execute(
                    select(CaseLocation)
                    .where(CaseLocation.case_id == case_id, CaseLocation.review_status != "rejected")
                    .options(*self._load_options())
                )
            ).scalars()
        )
        locations.sort(key=lambda item: (item.occurred_on is None, item.occurred_on or date.max, item.name))
        return [
            self._read(item, include_evidence_details=include_evidence_details)
            for item in locations
        ]

    async def create(self, case_id: uuid.UUID, data: LocationCreate, user_id: uuid.UUID) -> LocationRead:
        await self._require_case(case_id)
        if data.source_id is not None:
            await self._require_source(case_id, data.source_id)
        evidence = await self._validated_evidence(case_id, data.evidence_ids)
        people = await self._validated_people(case_id, data.person_ids)
        values = data.model_dump(exclude={"evidence_ids", "person_ids"})
        values["source_url"] = str(data.source_url) if data.source_url else None
        location = CaseLocation(
            case_id=case_id,
            created_by_user_id=user_id,
            ai_suggested=False,
            review_status="confirmed",
            **values,
        )
        self.db.add(location)
        await self.db.flush()
        self.db.add_all(
            [
                CaseLocationEvidence(
                    location_id=location.id,
                    evidence_id=item.id,
                    created_by_user_id=user_id,
                )
                for item in evidence
            ]
        )
        self.db.add_all(
            [
                CaseLocationPerson(
                    location_id=location.id,
                    person_id=person.id,
                    created_by_user_id=user_id,
                )
                for person in people
            ]
        )
        await self.db.commit()
        return await self.get(case_id, location.id)

    async def get(self, case_id: uuid.UUID, location_id: uuid.UUID) -> LocationRead:
        location = await self._location(case_id, location_id, load_links=True)
        return self._read(location)

    async def update(self, case_id: uuid.UUID, location_id: uuid.UUID, data: LocationPatch) -> LocationRead:
        location = await self._location(case_id, location_id)
        if data.source_id is not None:
            await self._require_source(case_id, data.source_id)
        values = data.model_dump(exclude_unset=True)
        if "source_url" in values:
            values["source_url"] = str(data.source_url) if data.source_url else None
        for key, value in values.items():
            setattr(location, key, value)
        await self.db.commit()
        return await self.get(case_id, location_id)

    async def delete(self, case_id: uuid.UUID, location_id: uuid.UUID) -> None:
        location = await self._location(case_id, location_id)
        await self.db.delete(location)
        await self.db.commit()

    async def _location(self, case_id: uuid.UUID, location_id: uuid.UUID, *, load_links: bool = False) -> CaseLocation:
        statement = select(CaseLocation).where(CaseLocation.id == location_id, CaseLocation.case_id == case_id)
        if load_links:
            statement = statement.options(*self._load_options())
        location = await self.db.scalar(statement)
        if location is None:
            raise AppError(404, "location_not_found", "Case location was not found")
        return location

    async def _require_case(self, case_id: uuid.UUID) -> None:
        if await self.db.scalar(select(Case.id).where(Case.id == case_id)) is None:
            raise AppError(404, "case_not_found", "Case was not found")

    async def _require_source(self, case_id: uuid.UUID, source_id: uuid.UUID) -> None:
        if await self.db.scalar(select(Source.id).where(Source.id == source_id, Source.case_id == case_id)) is None:
            raise AppError(422, "invalid_source", "Supporting source must belong to this case")

    async def _validated_evidence(
        self, case_id: uuid.UUID, evidence_ids: Sequence[uuid.UUID]
    ) -> Sequence[Evidence]:
        unique_ids: set[uuid.UUID] = set(evidence_ids)
        if not unique_ids:
            return []
        evidence = list(
            (
                await self.db.execute(
                    select(Evidence).where(
                        Evidence.case_id == case_id,
                        Evidence.id.in_(unique_ids),
                        Evidence.processing_status == "available",
                        Evidence.moderation_status == "visible",
                    )
                )
            ).scalars()
        )
        if len(evidence) != len(unique_ids):
            raise AppError(422, "invalid_evidence", "One or more evidence items are unavailable")
        return evidence

    async def _validated_people(
        self, case_id: uuid.UUID, person_ids: Sequence[uuid.UUID]
    ) -> Sequence[Person]:
        unique_ids: set[uuid.UUID] = set(person_ids)
        if not unique_ids:
            return []
        people = list(
            (
                await self.db.execute(
                    select(Person).where(Person.case_id == case_id, Person.id.in_(unique_ids))
                )
            ).scalars()
        )
        if len(people) != len(unique_ids):
            raise AppError(422, "invalid_people", "One or more people do not belong to this case")
        return people

    @staticmethod
    def _load_options() -> tuple[Any, ...]:
        return (
            selectinload(CaseLocation.source),
            selectinload(CaseLocation.evidence_links).selectinload(CaseLocationEvidence.evidence),
            selectinload(CaseLocation.person_links).selectinload(CaseLocationPerson.person),
        )

    @staticmethod
    def _read(
        item: CaseLocation, *, include_evidence_details: bool = True
    ) -> LocationRead:
        return LocationRead(
            id=item.id, case_id=item.case_id, name=item.name, description=item.description,
            latitude=item.latitude, longitude=item.longitude,
            location_type=cast(LocationType, item.location_type),
            occurred_on=item.occurred_on, precision=cast(Precision, item.precision),
            verification_status=cast(VerificationStatus, item.verification_status), source_id=item.source_id,
            source_url=item.source_url, source_title=item.source.title if item.source else None,
            ai_suggested=item.ai_suggested,
            review_status=cast(ReviewStatus, item.review_status),
            created_by_user_id=item.created_by_user_id, created_at=item.created_at,
            updated_at=item.updated_at,
            evidence=[
                to_evidence_read(
                    link.evidence, include_details=include_evidence_details
                )
                for link in item.evidence_links
                if link.evidence.moderation_status == "visible"
            ],
            people=[to_linked_person(link.person) for link in item.person_links],
        )
