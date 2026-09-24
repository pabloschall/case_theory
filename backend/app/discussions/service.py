import uuid
from collections import Counter
from datetime import timedelta
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cases.models import Case
from app.cases.schemas import SourceRead
from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.discussions.models import (
    DiscussionComment,
    DiscussionReaction,
    DiscussionThread,
    DiscussionThreadSource,
    DiscussionThreadVote,
)
from app.discussions.schemas import (
    AuthorRead,
    CommentCreate,
    CommentRead,
    ReactionEmoji,
    ReactionRead,
    ReactionToggle,
    ThreadCreate,
    ThreadRead,
    ThreadType,
    ThreadVoteRead,
)
from app.evidence.models import DiscussionThreadEvidence, Evidence
from app.evidence.service import to_evidence_read
from app.people.models import DiscussionThreadPerson, Person
from app.people.service import to_linked_person
from app.users.models import User


class DiscussionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_threads(
        self,
        case_id: uuid.UUID,
        current_user_id: uuid.UUID | None,
        *,
        cursor: uuid.UUID | None = None,
        limit: int = 10,
        include_evidence_details: bool = True,
    ) -> tuple[list[ThreadRead], uuid.UUID | None, bool, int, int, int, int]:
        await self._require_case(case_id)
        vote_count = (
            select(func.count(DiscussionThreadVote.id))
            .where(DiscussionThreadVote.thread_id == DiscussionThread.id)
            .correlate(DiscussionThread)
            .scalar_subquery()
        )
        statement = select(DiscussionThread).where(DiscussionThread.case_id == case_id)
        if cursor is not None:
            anchor = await self.db.scalar(
                select(DiscussionThread).where(
                    DiscussionThread.id == cursor,
                    DiscussionThread.case_id == case_id,
                )
            )
            if anchor is None:
                raise AppError(400, "invalid_cursor", "Discussion cursor is invalid")
            anchor_vote_count = int(
                await self.db.scalar(
                    select(func.count(DiscussionThreadVote.id)).where(
                        DiscussionThreadVote.thread_id == anchor.id
                    )
                )
                or 0
            )
            statement = statement.where(
                or_(
                    vote_count < anchor_vote_count,
                    and_(
                        vote_count == anchor_vote_count,
                        DiscussionThread.updated_at < anchor.updated_at,
                    ),
                    and_(
                        vote_count == anchor_vote_count,
                        DiscussionThread.updated_at == anchor.updated_at,
                        DiscussionThread.id < anchor.id,
                    ),
                )
            )
        result = await self.db.execute(
            statement
            .options(
                selectinload(DiscussionThread.author).selectinload(User.profile),
                selectinload(DiscussionThread.comments)
                .selectinload(DiscussionComment.author)
                .selectinload(User.profile),
                selectinload(DiscussionThread.comments).selectinload(DiscussionComment.reactions),
                selectinload(DiscussionThread.evidence_links).selectinload(
                    DiscussionThreadEvidence.evidence
                ),
                selectinload(DiscussionThread.person_links).selectinload(
                    DiscussionThreadPerson.person
                ),
                selectinload(DiscussionThread.source_links).selectinload(
                    DiscussionThreadSource.source
                ),
                selectinload(DiscussionThread.votes),
            )
            .order_by(
                vote_count.desc(),
                DiscussionThread.updated_at.desc(),
                DiscussionThread.id.desc(),
            )
            .limit(limit + 1)
        )
        records = list(result.scalars())
        has_more = len(records) > limit
        records = records[:limit]
        total = int(
            await self.db.scalar(
                select(func.count(DiscussionThread.id)).where(
                    DiscussionThread.case_id == case_id
                )
            )
            or 0
        )
        active_count = int(
            await self.db.scalar(
                select(func.count(DiscussionThread.id)).where(
                    DiscussionThread.case_id == case_id,
                    DiscussionThread.updated_at >= utc_now() - timedelta(days=30),
                )
            )
            or 0
        )
        comment_count = int(
            await self.db.scalar(
                select(func.count(DiscussionComment.id))
                .join(DiscussionThread, DiscussionThread.id == DiscussionComment.thread_id)
                .where(
                    DiscussionThread.case_id == case_id,
                    DiscussionComment.moderation_status == "visible",
                )
            )
            or 0
        )
        evidence_link_count = int(
            await self.db.scalar(
                select(func.count(DiscussionThreadEvidence.id))
                .join(DiscussionThread, DiscussionThread.id == DiscussionThreadEvidence.thread_id)
                .where(DiscussionThread.case_id == case_id)
            )
            or 0
        )
        source_count = int(
            await self.db.scalar(
                select(func.count(DiscussionThreadSource.id))
                .join(DiscussionThread, DiscussionThread.id == DiscussionThreadSource.thread_id)
                .where(DiscussionThread.case_id == case_id)
            )
            or 0
        )
        items = [
            self._to_thread_read(
                thread,
                current_user_id,
                include_evidence_details=include_evidence_details,
            )
            for thread in records
        ]
        next_cursor = records[-1].id if has_more and records else None
        return (
            items,
            next_cursor,
            has_more,
            total,
            active_count,
            evidence_link_count + source_count,
            comment_count,
        )

    async def create_thread(
        self, case_id: uuid.UUID, current_user: User, data: ThreadCreate
    ) -> ThreadRead:
        await self._require_case(case_id)
        thread = DiscussionThread(
            case_id=case_id,
            title=data.title,
            body=data.body,
            thread_type=data.thread_type,
            created_by_user_id=current_user.id,
        )
        self.db.add(thread)
        if data.evidence_ids:
            evidence = await self._validated_evidence(case_id, data.evidence_ids)
            await self.db.flush()
            self.db.add_all(
                [
                    DiscussionThreadEvidence(
                        thread_id=thread.id,
                        evidence_id=item.id,
                        created_by_user_id=current_user.id,
                    )
                    for item in evidence
                ]
            )
        if data.person_ids:
            people = await self._validated_people(case_id, data.person_ids)
            await self.db.flush()
            self.db.add_all(
                [
                    DiscussionThreadPerson(
                        thread_id=thread.id,
                        person_id=person.id,
                        created_by_user_id=current_user.id,
                    )
                    for person in people
                ]
            )
        await self.db.commit()
        return await self.get_thread(case_id, thread.id, current_user.id)

    async def add_comment(
        self,
        case_id: uuid.UUID,
        thread_id: uuid.UUID,
        current_user: User,
        data: CommentCreate,
    ) -> ThreadRead:
        thread = await self.db.scalar(
            select(DiscussionThread).where(
                DiscussionThread.id == thread_id,
                DiscussionThread.case_id == case_id,
            )
        )
        if thread is None:
            raise AppError(404, "thread_not_found", "Discussion thread was not found")
        self.db.add(
            DiscussionComment(
                thread_id=thread.id,
                body=data.body,
                created_by_user_id=current_user.id,
            )
        )
        thread.updated_at = utc_now()
        await self.db.commit()
        return await self.get_thread(case_id, thread.id, current_user.id)

    async def toggle_reaction(
        self,
        case_id: uuid.UUID,
        thread_id: uuid.UUID,
        comment_id: uuid.UUID,
        current_user_id: uuid.UUID,
        data: ReactionToggle,
    ) -> ThreadRead:
        comment = await self.db.scalar(
            select(DiscussionComment)
            .join(DiscussionThread, DiscussionThread.id == DiscussionComment.thread_id)
            .where(
                DiscussionComment.id == comment_id,
                DiscussionComment.thread_id == thread_id,
                DiscussionThread.case_id == case_id,
            )
        )
        if comment is None:
            raise AppError(404, "comment_not_found", "Discussion comment was not found")
        reaction = await self.db.scalar(
            select(DiscussionReaction).where(
                DiscussionReaction.comment_id == comment.id,
                DiscussionReaction.user_id == current_user_id,
                DiscussionReaction.emoji == data.emoji,
            )
        )
        if reaction is None:
            self.db.add(
                DiscussionReaction(
                    comment_id=comment.id,
                    user_id=current_user_id,
                    emoji=data.emoji,
                )
            )
        else:
            await self.db.delete(reaction)
        await self.db.commit()
        return await self.get_thread(case_id, thread_id, current_user_id)

    async def toggle_vote(
        self,
        case_id: uuid.UUID,
        thread_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> ThreadVoteRead:
        thread_exists = await self.db.scalar(
            select(DiscussionThread.id).where(
                DiscussionThread.id == thread_id,
                DiscussionThread.case_id == case_id,
            )
        )
        if thread_exists is None:
            raise AppError(404, "thread_not_found", "Discussion thread was not found")
        vote = await self.db.scalar(
            select(DiscussionThreadVote).where(
                DiscussionThreadVote.thread_id == thread_id,
                DiscussionThreadVote.user_id == current_user_id,
            )
        )
        voted_by_me = vote is None
        if vote is None:
            self.db.add(
                DiscussionThreadVote(
                    thread_id=thread_id,
                    user_id=current_user_id,
                )
            )
        else:
            await self.db.delete(vote)
        await self.db.commit()
        count = int(
            await self.db.scalar(
                select(func.count(DiscussionThreadVote.id)).where(
                    DiscussionThreadVote.thread_id == thread_id
                )
            )
            or 0
        )
        return ThreadVoteRead(vote_count=count, voted_by_me=voted_by_me)

    async def get_thread(
        self, case_id: uuid.UUID, thread_id: uuid.UUID, current_user_id: uuid.UUID
    ) -> ThreadRead:
        thread = await self.db.scalar(
            select(DiscussionThread)
            .where(DiscussionThread.id == thread_id, DiscussionThread.case_id == case_id)
            .options(
                selectinload(DiscussionThread.author).selectinload(User.profile),
                selectinload(DiscussionThread.comments)
                .selectinload(DiscussionComment.author)
                .selectinload(User.profile),
                selectinload(DiscussionThread.comments).selectinload(DiscussionComment.reactions),
                selectinload(DiscussionThread.evidence_links).selectinload(
                    DiscussionThreadEvidence.evidence
                ),
                selectinload(DiscussionThread.person_links).selectinload(
                    DiscussionThreadPerson.person
                ),
                selectinload(DiscussionThread.source_links).selectinload(
                    DiscussionThreadSource.source
                ),
                selectinload(DiscussionThread.votes),
            )
        )
        if thread is None:
            raise AppError(404, "thread_not_found", "Discussion thread was not found")
        return self._to_thread_read(thread, current_user_id)

    async def _require_case(self, case_id: uuid.UUID) -> None:
        if await self.db.scalar(select(Case.id).where(Case.id == case_id)) is None:
            raise AppError(404, "case_not_found", "Case was not found")

    def _to_thread_read(
        self,
        thread: DiscussionThread,
        current_user_id: uuid.UUID | None,
        *,
        include_evidence_details: bool = True,
    ) -> ThreadRead:
        return ThreadRead(
            id=thread.id,
            title=thread.title,
            body=thread.body,
            thread_type=cast(ThreadType, thread.thread_type),
            author=_author(thread.author),
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            comments=[
                _comment(comment, current_user_id)
                for comment in thread.comments
                if comment.moderation_status == "visible"
            ],
            evidence=[
                to_evidence_read(
                    link.evidence, include_details=include_evidence_details
                )
                for link in thread.evidence_links
                if link.evidence.moderation_status == "visible"
            ],
            people=[to_linked_person(link.person) for link in thread.person_links],
            sources=[SourceRead.model_validate(link.source) for link in thread.source_links],
            ai_generated=thread.ai_generated,
            review_status=thread.review_status,
            vote_count=len(thread.votes),
            voted_by_me=any(
                vote.user_id == current_user_id for vote in thread.votes
            ),
        )

    async def _validated_evidence(
        self, case_id: uuid.UUID, evidence_ids: list[uuid.UUID]
    ) -> list[Evidence]:
        unique_ids = set(evidence_ids)
        result = await self.db.execute(
            select(Evidence).where(
                Evidence.case_id == case_id,
                Evidence.id.in_(unique_ids),
                Evidence.processing_status == "available",
                Evidence.moderation_status == "visible",
            )
        )
        evidence = list(result.scalars())
        if len(evidence) != len(unique_ids):
            raise AppError(422, "invalid_evidence", "One or more evidence items are unavailable")
        return evidence

    async def _validated_people(
        self, case_id: uuid.UUID, person_ids: list[uuid.UUID]
    ) -> list[Person]:
        unique_ids = set(person_ids)
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


def _author(user: User) -> AuthorRead:
    return AuthorRead(
        id=user.id,
        username=user.username,
        display_name=user.profile.display_name,
    )


def _comment(comment: DiscussionComment, current_user_id: uuid.UUID | None) -> CommentRead:
    counts = Counter(reaction.emoji for reaction in comment.reactions)
    mine = {reaction.emoji for reaction in comment.reactions if reaction.user_id == current_user_id}
    return CommentRead(
        id=comment.id,
        body=comment.body,
        author=_author(comment.author),
        created_at=comment.created_at,
        reactions=[
            ReactionRead(
                emoji=cast(ReactionEmoji, emoji), count=count, reacted_by_me=emoji in mine
            )
            for emoji, count in sorted(counts.items())
        ],
    )
