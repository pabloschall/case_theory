import re
import uuid
from collections import Counter
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cases.models import Case, Source
from app.common.errors import AppError
from app.evidence.models import Evidence
from app.evidence.schemas import EvidenceRead
from app.evidence.service import to_evidence_read
from app.people.models import Person, PersonEvidence, PersonNote, PersonRelationship
from app.people.schemas import (
    EntityType,
    LinkedPersonRead,
    PersonCategory,
    PersonCreate,
    PersonNoteCreate,
    PersonNoteRead,
    PersonPatch,
    PersonRead,
    RelationshipCreate,
    RelationshipPatch,
    RelationshipRead,
    ReviewStatus,
)
from app.users.models import User


def to_linked_person(person: Person) -> LinkedPersonRead:
    return LinkedPersonRead(
        id=person.id,
        name=person.name,
        role=person.role,
        category=cast(PersonCategory, person.category),
        entity_type=cast(EntityType, person.entity_type),
        photo_url=person.photo_url,
    )


class PeopleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_people(self, case_id: uuid.UUID) -> list[PersonRead]:
        await self._require_case(case_id)
        people = list(
            (
                await self.db.execute(
                    select(Person)
                    .where(Person.case_id == case_id, Person.review_status != "rejected")
                    .options(
                        selectinload(Person.evidence_links).selectinload(PersonEvidence.evidence),
                        selectinload(Person.notes),
                    )
                    .order_by(Person.is_primary.desc(), Person.name)
                )
            ).scalars()
        )
        counts = await self._connection_counts(case_id)
        return [self._person_read(person, counts[person.id]) for person in people]

    async def get_person(self, case_id: uuid.UUID, person_id: uuid.UUID) -> PersonRead:
        person = await self._person(case_id, person_id)
        counts = await self._connection_counts(case_id)
        return self._person_read(person, counts[person.id])

    async def create_person(self, case_id: uuid.UUID, data: PersonCreate, user_id: uuid.UUID) -> PersonRead:
        await self._require_case(case_id)
        values = data.model_dump()
        values["photo_url"] = str(data.photo_url) if data.photo_url else None
        person = Person(
            case_id=case_id,
            slug=_slug(data.name, str(uuid.uuid4())[:8]),
            created_by_user_id=user_id,
            review_status="confirmed",
            **values,
        )
        self.db.add(person)
        await self.db.commit()
        return await self.get_person(case_id, person.id)

    async def update_person(self, case_id: uuid.UUID, person_id: uuid.UUID, data: PersonPatch) -> PersonRead:
        person = await self._person(case_id, person_id)
        values = data.model_dump(exclude_unset=True)
        if "photo_url" in values:
            values["photo_url"] = str(data.photo_url) if data.photo_url else None
        for key, value in values.items():
            setattr(person, key, value)
        if data.name is not None:
            person.slug = _slug(data.name, str(person.id)[:8])
        await self.db.commit()
        return await self.get_person(case_id, person_id)

    async def list_relationships(self, case_id: uuid.UUID) -> list[RelationshipRead]:
        await self._require_case(case_id)
        relationships = (
            await self.db.execute(
                select(PersonRelationship)
                .where(PersonRelationship.case_id == case_id, PersonRelationship.review_status != "rejected")
                .options(selectinload(PersonRelationship.source))
                .order_by(PersonRelationship.created_at)
            )
        ).scalars()
        return [self._relationship_read(item) for item in relationships]

    async def create_relationship(
        self, case_id: uuid.UUID, data: RelationshipCreate, user_id: uuid.UUID
    ) -> RelationshipRead:
        await self._require_people(case_id, {data.source_person_id, data.target_person_id})
        if data.source_id is not None:
            await self._require_source(case_id, data.source_id)
        values = data.model_dump()
        values["source_url"] = str(data.source_url) if data.source_url else None
        relationship = PersonRelationship(
            case_id=case_id,
            created_by_user_id=user_id,
            review_status="suggested" if data.ai_suggested else "confirmed",
            **values,
        )
        self.db.add(relationship)
        await self.db.commit()
        return await self._get_relationship(case_id, relationship.id)

    async def update_relationship(
        self, case_id: uuid.UUID, relationship_id: uuid.UUID, data: RelationshipPatch
    ) -> RelationshipRead:
        relationship = await self._relationship(case_id, relationship_id)
        values = data.model_dump(exclude_unset=True)
        if "source_url" in values:
            values["source_url"] = str(data.source_url) if data.source_url else None
        if data.source_id is not None:
            await self._require_source(case_id, data.source_id)
        for key, value in values.items():
            setattr(relationship, key, value)
        await self.db.commit()
        return await self._get_relationship(case_id, relationship_id)

    async def delete_relationship(self, case_id: uuid.UUID, relationship_id: uuid.UUID) -> None:
        relationship = await self._relationship(case_id, relationship_id)
        await self.db.delete(relationship)
        await self.db.commit()

    async def evidence(self, case_id: uuid.UUID, person_id: uuid.UUID) -> list[EvidenceRead]:
        await self._person(case_id, person_id)
        evidence = (
            await self.db.execute(
                select(Evidence)
                .join(PersonEvidence, PersonEvidence.evidence_id == Evidence.id)
                .where(
                    PersonEvidence.person_id == person_id,
                    Evidence.moderation_status == "visible",
                )
                .order_by(Evidence.created_at.desc())
            )
        ).scalars()
        return [to_evidence_read(item) for item in evidence]

    async def notes(self, case_id: uuid.UUID, person_id: uuid.UUID) -> list[PersonNoteRead]:
        await self._person(case_id, person_id)
        notes = (
            await self.db.execute(
                select(PersonNote)
                .where(PersonNote.person_id == person_id)
                .options(selectinload(PersonNote.author).selectinload(User.profile))
                .order_by(PersonNote.created_at.desc())
            )
        ).scalars()
        return [self._note_read(note) for note in notes]

    async def create_note(
        self, case_id: uuid.UUID, person_id: uuid.UUID, data: PersonNoteCreate, user: User
    ) -> PersonNoteRead:
        await self._person(case_id, person_id)
        note = PersonNote(person_id=person_id, author_user_id=user.id, body=data.body)
        self.db.add(note)
        await self.db.commit()
        return (await self.notes(case_id, person_id))[0]

    async def update_note(
        self, case_id: uuid.UUID, person_id: uuid.UUID, note_id: uuid.UUID, data: PersonNoteCreate
    ) -> PersonNoteRead:
        note = await self._note(case_id, person_id, note_id)
        note.body = data.body
        await self.db.commit()
        return next(item for item in await self.notes(case_id, person_id) if item.id == note_id)

    async def delete_note(self, case_id: uuid.UUID, person_id: uuid.UUID, note_id: uuid.UUID) -> None:
        note = await self._note(case_id, person_id, note_id)
        await self.db.delete(note)
        await self.db.commit()

    async def _person(self, case_id: uuid.UUID, person_id: uuid.UUID) -> Person:
        person = await self.db.scalar(
            select(Person)
            .where(Person.id == person_id, Person.case_id == case_id)
            .options(
                selectinload(Person.evidence_links).selectinload(PersonEvidence.evidence),
                selectinload(Person.notes),
            )
        )
        if person is None:
            raise AppError(404, "person_not_found", "Person or entity was not found")
        return person

    async def _relationship(self, case_id: uuid.UUID, relationship_id: uuid.UUID) -> PersonRelationship:
        relationship = await self.db.scalar(
            select(PersonRelationship).where(
                PersonRelationship.id == relationship_id,
                PersonRelationship.case_id == case_id,
            )
        )
        if relationship is None:
            raise AppError(404, "relationship_not_found", "Relationship was not found")
        return relationship

    async def _get_relationship(self, case_id: uuid.UUID, relationship_id: uuid.UUID) -> RelationshipRead:
        relationship = await self.db.scalar(
            select(PersonRelationship)
            .where(PersonRelationship.id == relationship_id, PersonRelationship.case_id == case_id)
            .options(selectinload(PersonRelationship.source))
        )
        if relationship is None:
            raise AppError(404, "relationship_not_found", "Relationship was not found")
        return self._relationship_read(relationship)

    async def _note(self, case_id: uuid.UUID, person_id: uuid.UUID, note_id: uuid.UUID) -> PersonNote:
        note = await self.db.scalar(
            select(PersonNote)
            .join(Person, Person.id == PersonNote.person_id)
            .where(PersonNote.id == note_id, PersonNote.person_id == person_id, Person.case_id == case_id)
        )
        if note is None:
            raise AppError(404, "note_not_found", "Person note was not found")
        return note

    async def _connection_counts(self, case_id: uuid.UUID) -> Counter[uuid.UUID]:
        rows = await self.db.execute(
            select(PersonRelationship.source_person_id, PersonRelationship.target_person_id).where(
                PersonRelationship.case_id == case_id,
                PersonRelationship.review_status != "rejected",
            )
        )
        counts: Counter[uuid.UUID] = Counter()
        for source_id, target_id in rows:
            counts[source_id] += 1
            counts[target_id] += 1
        return counts

    async def _require_people(self, case_id: uuid.UUID, person_ids: set[uuid.UUID]) -> None:
        found = set(
            (
                await self.db.execute(select(Person.id).where(Person.case_id == case_id, Person.id.in_(person_ids)))
            ).scalars()
        )
        if found != person_ids:
            raise AppError(422, "invalid_people", "Relationship entities must belong to this case")

    async def _require_source(self, case_id: uuid.UUID, source_id: uuid.UUID) -> None:
        if await self.db.scalar(select(Source.id).where(Source.id == source_id, Source.case_id == case_id)) is None:
            raise AppError(422, "invalid_source", "Supporting source must belong to this case")

    async def _require_case(self, case_id: uuid.UUID) -> None:
        if await self.db.scalar(select(Case.id).where(Case.id == case_id)) is None:
            raise AppError(404, "case_not_found", "Case was not found")

    @staticmethod
    def _person_read(person: Person, connection_count: int) -> PersonRead:
        return PersonRead(
            id=person.id,
            case_id=person.case_id,
            name=person.name,
            slug=person.slug,
            role=person.role,
            category=cast(PersonCategory, person.category),
            entity_type=cast(EntityType, person.entity_type),
            photo_url=person.photo_url,
            date_of_birth=person.date_of_birth,
            place_of_birth=person.place_of_birth,
            relationship_to_primary=person.relationship_to_primary,
            summary=person.summary,
            is_primary=person.is_primary,
            ai_suggested=person.ai_suggested,
            review_status=cast(ReviewStatus, person.review_status),
            connection_count=connection_count,
            evidence_count=sum(
                link.evidence.moderation_status == "visible"
                for link in person.evidence_links
            ),
            notes_count=len(person.notes),
            created_at=person.created_at,
            updated_at=person.updated_at,
        )

    @staticmethod
    def _relationship_read(item: PersonRelationship) -> RelationshipRead:
        return RelationshipRead(
            id=item.id,
            case_id=item.case_id,
            source_person_id=item.source_person_id,
            target_person_id=item.target_person_id,
            relationship_type=item.relationship_type,
            label=item.label,
            description=item.description,
            confidence=item.confidence,
            source_type=item.source_type,
            source_id=item.source_id,
            source_url=item.source_url,
            source_title=item.source.title if item.source else None,
            ai_suggested=item.ai_suggested,
            review_status=cast(ReviewStatus, item.review_status),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _note_read(note: PersonNote) -> PersonNoteRead:
        return PersonNoteRead(
            id=note.id,
            body=note.body,
            author_user_id=note.author_user_id,
            author_name=note.author.profile.display_name,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )


def _slug(value: str, suffix: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:240] or "entity"
    return f"{normalized}-{suffix}"
