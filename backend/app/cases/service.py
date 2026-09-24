import re
import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cases.models import Case, CaseFollower, CaseGenerationJob, CaseSummary, TimelineEvent, TimelineEventSource
from app.cases.schemas import (
    AdminCaseListItem,
    CaseCreate,
    CaseListItem,
    CaseOwnerRead,
    CaseRead,
    CaseSourceRead,
    SourceRead,
    SummaryRead,
    TimelineEventCreate,
    TimelineEventRead,
)
from app.common.errors import AppError
from app.discussions.models import DiscussionComment, DiscussionThread
from app.evidence.models import Evidence, TimelineEventEvidence
from app.evidence.service import to_evidence_read
from app.people.models import Person, TimelineEventPerson
from app.people.service import to_linked_person
from app.subscriptions.permissions import PermissionService
from app.users.models import User


def _slug(value: str, suffix: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:140] or "case"
    return f"{normalized}-{suffix}"


def to_case_read(
    case: Case,
    current_user_id: uuid.UUID | None,
    *,
    is_following: bool = False,
    include_evidence_details: bool = False,
) -> CaseRead:
    summary = next((item for item in case.summaries if item.is_current), None)
    return CaseRead(
        id=case.id,
        public_id=case.public_id,
        slug=case.slug,
        title=case.title,
        victim_names=case.victim_names,
        year=case.year,
        location=case.location,
        status=case.status,
        privacy=case.privacy,
        owner=CaseOwnerRead(
            id=case.owner.id,
            username=case.owner.username,
            display_name=case.owner.profile.display_name,
        ),
        is_owner=case.created_by_user_id == current_user_id,
        is_following=is_following,
        ai_research_status=case.ai_research_status,
        ai_error_message=case.ai_error_message,
        cover_image_url=case.cover_image_url,
        summary=SummaryRead.model_validate(summary) if summary else None,
        timeline=[
            TimelineEventRead(
                id=item.id,
                date_label=item.date_label,
                occurred_on=item.occurred_on,
                date_precision=item.date_precision,
                title=item.title,
                description=item.description,
                verification_status=item.verification_status,
                confidence=item.confidence,
                source_note=item.source_note,
                ai_generated=item.ai_generated,
                created_by_user_id=item.created_by_user_id,
                sources=[SourceRead.model_validate(link.source) for link in item.source_links],
                evidence=[
                    to_evidence_read(
                        link.evidence, include_details=include_evidence_details
                    )
                    for link in item.evidence_links
                    if link.evidence.moderation_status == "visible"
                ],
                people=[to_linked_person(link.person) for link in item.person_links],
            )
            for item in sorted(
                case.timeline,
                key=lambda item: (
                    item.occurred_on is None,
                    item.occurred_on or date.max,
                    item.created_at,
                    str(item.id),
                ),
            )
        ],
        sources=[SourceRead.model_validate(source) for source in sorted(case.sources, key=lambda item: item.position)],
        external_sources=[CaseSourceRead.model_validate(source) for source in case.external_sources],
        created_at=case.created_at,
    )


def to_list_item(
    case: Case,
    current_user_id: uuid.UUID | None,
    discussion_count: int = 0,
    *,
    is_following: bool = False,
) -> CaseListItem:
    return CaseListItem(
        id=case.id,
        slug=case.slug,
        title=case.title,
        victim_names=case.victim_names,
        year=case.year,
        location=case.location,
        privacy=case.privacy,
        is_owner=case.created_by_user_id == current_user_id,
        is_following=is_following,
        ai_research_status=case.ai_research_status,
        cover_image_url=case.cover_image_url,
        discussion_count=discussion_count,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def to_admin_list_item(case: Case) -> AdminCaseListItem:
    return AdminCaseListItem(
        **to_list_item(case, case.created_by_user_id).model_dump(),
        status=case.status,
    )


class CaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: CaseCreate, user: User) -> tuple[Case, CaseGenerationJob | None]:
        permissions = PermissionService(self.db)
        is_unlimited_manual_public = data.creation_mode == "manual" and data.privacy == "public"
        await permissions.require_case_creation(
            user, enforce_limit=not is_unlimited_manual_public
        )
        if data.creation_mode == "manual":
            await permissions.require(
                user,
                "case.create",
                required_tier=2,
                message="Manual case creation is available to Investigator plans",
            )
        else:
            await permissions.require(user, "case.create_ai", required_tier=1)
        if data.privacy == "private":
            await permissions.require(
                user,
                "case.private",
                required_tier=2,
                message="Private cases require an Investigator plan",
            )
        case_id = uuid.uuid4()
        if data.creation_mode == "ai":
            permissions.record_ai_case(user, case_id)
        title = data.victim_names.strip()
        if data.year is not None:
            title = f"{title} — {data.year}"
        case = Case(
            id=case_id,
            slug=_slug(data.victim_names, str(case_id)[:8]),
            title=title,
            victim_names=data.victim_names.strip(),
            year=data.year,
            location=data.location,
            intake_notes=data.additional_context.strip() if data.additional_context else None,
            privacy=data.privacy,
            ai_research_status="queued" if data.creation_mode == "ai" else "complete",
            cover_image_url=data.banner_template if data.creation_mode == "manual" else None,
            counts_toward_weekly_limit=not is_unlimited_manual_public,
            created_by_user_id=user.id,
        )
        self.db.add(case)
        await self.db.flush()
        job = None
        if data.creation_mode == "ai":
            job = CaseGenerationJob(case_id=case.id)
            self.db.add(job)
        else:
            self.db.add(
                CaseSummary(
                    case_id=case.id,
                    body=data.summary or "",
                    source="user",
                    ai_model=None,
                    is_current=True,
                )
            )
        await self.db.commit()
        return case, job

    async def get(self, case_id: uuid.UUID) -> Case:
        case = await self.db.scalar(
            select(Case)
            .where(Case.id == case_id)
            .options(
                selectinload(Case.summaries),
                selectinload(Case.owner).selectinload(User.profile),
                selectinload(Case.sources),
                selectinload(Case.external_sources),
                selectinload(Case.timeline)
                .selectinload(TimelineEvent.source_links)
                .selectinload(TimelineEventSource.source),
                selectinload(Case.timeline)
                .selectinload(TimelineEvent.evidence_links)
                .selectinload(TimelineEventEvidence.evidence),
                selectinload(Case.timeline)
                .selectinload(TimelineEvent.person_links)
                .selectinload(TimelineEventPerson.person),
            )
        )
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        return case

    async def cover_object_key(self, case_id: uuid.UUID) -> str:
        object_key = await self.db.scalar(
            select(Case.cover_image_object_key).where(Case.id == case_id)
        )
        if object_key is None:
            raise AppError(404, "case_cover_not_found", "Case cover was not found")
        return object_key

    async def search(
        self,
        query: str | None = None,
        sort: str = "newest",
        *,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[list[Case], int]:
        statement = select(Case).where(Case.privacy == "public")
        if query:
            normalized_query = query.strip()
            pattern = f"%{normalized_query}%"
            text_match = or_(
                Case.title.ilike(pattern),
                Case.victim_names.ilike(pattern),
                Case.location.ilike(pattern),
            )
            statement = statement.where(
                or_(text_match, Case.year == int(normalized_query))
                if normalized_query.isdigit()
                else text_match
            )
        if sort == "popular":
            thread_count = (
                select(func.count(DiscussionThread.id))
                .where(DiscussionThread.case_id == Case.id)
                .correlate(Case)
                .scalar_subquery()
            )
            comment_count = (
                select(func.count(DiscussionComment.id))
                .join(DiscussionThread, DiscussionThread.id == DiscussionComment.thread_id)
                .where(DiscussionThread.case_id == Case.id)
                .correlate(Case)
                .scalar_subquery()
            )
            statement = statement.order_by((thread_count + comment_count).desc(), Case.created_at.desc())
        else:
            statement = statement.order_by(Case.created_at.desc())
        total = await self.db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
        result = await self.db.execute(
            statement.options(selectinload(Case.owner).selectinload(User.profile))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total or 0

    async def discussion_counts(self, case_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not case_ids:
            return {}
        counts = dict.fromkeys(case_ids, 0)
        thread_rows = await self.db.execute(
            select(DiscussionThread.case_id, func.count(DiscussionThread.id))
            .where(DiscussionThread.case_id.in_(case_ids))
            .group_by(DiscussionThread.case_id)
        )
        for case_id, count in thread_rows:
            counts[case_id] += count
        comment_rows = await self.db.execute(
            select(DiscussionThread.case_id, func.count(DiscussionComment.id))
            .join(DiscussionComment, DiscussionComment.thread_id == DiscussionThread.id)
            .where(DiscussionThread.case_id.in_(case_ids))
            .group_by(DiscussionThread.case_id)
        )
        for case_id, count in comment_rows:
            counts[case_id] += count
        return counts

    async def following(self, user_id: uuid.UUID) -> list[Case]:
        result = await self.db.execute(
            select(Case)
            .join(CaseFollower, CaseFollower.case_id == Case.id)
            .where(CaseFollower.user_id == user_id)
            .options(selectinload(Case.owner).selectinload(User.profile))
            .order_by(Case.updated_at.desc())
        )
        return list(result.scalars())

    async def is_following(self, case_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return (
            await self.db.scalar(
                select(CaseFollower.id).where(
                    CaseFollower.case_id == case_id,
                    CaseFollower.user_id == user_id,
                )
            )
            is not None
        )

    async def following_case_ids(
        self, case_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> set[uuid.UUID]:
        if not case_ids:
            return set()
        result = await self.db.scalars(
            select(CaseFollower.case_id).where(
                CaseFollower.case_id.in_(case_ids),
                CaseFollower.user_id == user_id,
            )
        )
        return set(result)

    async def follow(self, case_id: uuid.UUID, user_id: uuid.UUID) -> None:
        case = await self.db.scalar(select(Case).where(Case.id == case_id))
        if case is None or case.privacy != "public":
            raise AppError(404, "case_not_found", "Case was not found")
        if case.created_by_user_id == user_id:
            raise AppError(409, "owner_cannot_follow", "Owned cases already appear under My Cases")
        if not await self.is_following(case_id, user_id):
            self.db.add(CaseFollower(case_id=case_id, user_id=user_id))
            await self.db.commit()

    async def unfollow(self, case_id: uuid.UUID, user_id: uuid.UUID) -> None:
        follower = await self.db.scalar(
            select(CaseFollower).where(
                CaseFollower.case_id == case_id,
                CaseFollower.user_id == user_id,
            )
        )
        if follower is not None:
            await self.db.delete(follower)
            await self.db.commit()

    async def mine(self, user_id: uuid.UUID) -> list[Case]:
        result = await self.db.execute(
            select(Case)
            .where(Case.created_by_user_id == user_id)
            .options(selectinload(Case.owner).selectinload(User.profile))
            .order_by(Case.updated_at.desc())
        )
        return list(result.scalars())

    async def list_all(self) -> list[Case]:
        result = await self.db.execute(select(Case).order_by(Case.created_at.desc()))
        return list(result.scalars())

    async def delete(self, case_id: uuid.UUID) -> None:
        case = await self.db.scalar(select(Case).where(Case.id == case_id))
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        await self.db.delete(case)
        await self.db.commit()

    async def queue_research(self, case_id: uuid.UUID, user: User) -> CaseGenerationJob:
        await PermissionService(self.db).require(
            user,
            "ai.research",
            required_tier=3,
            message="Researching an existing case requires a Lead Investigator plan",
        )
        case = await self.db.scalar(select(Case).where(Case.id == case_id))
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        if case.ai_research_status not in {"complete", "failed"}:
            raise AppError(409, "research_in_progress", "Research is already in progress")
        case.ai_research_status = "queued"
        case.ai_error_message = None
        case.cover_image_url = None
        job = CaseGenerationJob(case_id=case.id)
        self.db.add(job)
        await self.db.commit()
        return job

    async def update_privacy(self, case_id: uuid.UUID, privacy: str, user: User) -> Case:
        case = await self.db.scalar(select(Case).where(Case.id == case_id))
        if case is None or (case.created_by_user_id != user.id and not user.is_admin):
            raise AppError(404, "case_not_found", "Case was not found")
        if privacy == "private" and not await PermissionService(self.db).allows(
            user.id, "case.private", is_admin=user.is_admin
        ):
            raise AppError(403, "private_case_upgrade_required", "Private cases require a paid plan")
        case.privacy = privacy
        await self.db.commit()
        return await self.get(case_id)

    async def create_timeline_event(
        self, case_id: uuid.UUID, data: TimelineEventCreate, user: User
    ) -> TimelineEventRead:
        if await self.db.scalar(select(Case.id).where(Case.id == case_id)) is None:
            raise AppError(404, "case_not_found", "Case was not found")
        evidence_ids = set(data.evidence_ids)
        person_ids = set(data.person_ids)
        evidence = []
        if evidence_ids:
            result = await self.db.execute(
                select(Evidence).where(
                    Evidence.case_id == case_id,
                    Evidence.id.in_(evidence_ids),
                    Evidence.processing_status == "available",
                    Evidence.moderation_status == "visible",
                )
            )
            evidence = list(result.scalars())
            if len(evidence) != len(evidence_ids):
                raise AppError(422, "invalid_evidence", "One or more evidence items are unavailable")
        people = []
        if person_ids:
            result = await self.db.execute(
                select(Person).where(Person.case_id == case_id, Person.id.in_(person_ids))
            )
            people = list(result.scalars())
            if len(people) != len(person_ids):
                raise AppError(422, "invalid_people", "One or more people do not belong to this case")
        event = TimelineEvent(
            case_id=case_id,
            date_label=data.occurred_on.strftime("%B %d, %Y").replace(" 0", " "),
            occurred_on=data.occurred_on,
            date_precision="exact",
            title=data.title,
            description=data.description,
            verification_status="unverified",
            confidence="unknown",
            source_note="Added by an investigator; review the attached evidence and sources.",
            ai_generated=False,
            created_by_user_id=user.id,
        )
        self.db.add(event)
        await self.db.flush()
        if evidence:
            self.db.add_all(
                [
                    TimelineEventEvidence(
                        timeline_event_id=event.id,
                        evidence_id=item.id,
                        created_by_user_id=user.id,
                    )
                    for item in evidence
                ]
            )
        if people:
            self.db.add_all(
                [
                    TimelineEventPerson(
                        timeline_event_id=event.id,
                        person_id=person.id,
                        created_by_user_id=user.id,
                    )
                    for person in people
                ]
            )
        await self.db.commit()
        case = await self.get(case_id)
        return next(
            item
            for item in to_case_read(case, user.id, include_evidence_details=True).timeline
            if item.id == event.id
        )
