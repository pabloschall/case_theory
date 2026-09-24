import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppError
from app.notes.models import CaseNotebookNote, CaseTimelineEntry
from app.notes.schemas import (
    ContributorAuthorRead,
    NotebookNotePage,
    NotebookNoteRead,
    NotebookNoteWrite,
    TimelineEntryRead,
    TimelineEntryWrite,
)
from app.users.models import User


class NotebookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_notes(
        self,
        case_id: uuid.UUID,
        current_user: User,
        *,
        cursor: uuid.UUID | None = None,
        limit: int = 20,
    ) -> NotebookNotePage:
        in_case = (
            CaseNotebookNote.case_id == case_id,
            CaseNotebookNote.author_user_id == current_user.id,
        )
        statement = select(CaseNotebookNote).where(*in_case).options(
            selectinload(CaseNotebookNote.author).selectinload(User.profile)
        )
        if cursor is not None:
            anchor = await self.db.scalar(
                select(CaseNotebookNote).where(CaseNotebookNote.id == cursor, *in_case)
            )
            if anchor is None:
                raise AppError(400, "invalid_cursor", "Notebook cursor is invalid")
            statement = statement.where(
                or_(
                    CaseNotebookNote.updated_at < anchor.updated_at,
                    and_(
                        CaseNotebookNote.updated_at == anchor.updated_at,
                        CaseNotebookNote.id < anchor.id,
                    ),
                )
            )
        notes = list(
            (
                await self.db.execute(
                    statement.order_by(
                        CaseNotebookNote.updated_at.desc(), CaseNotebookNote.id.desc()
                    ).limit(limit + 1)
                )
            ).scalars()
        )
        has_more = len(notes) > limit
        page_items = notes[:limit]
        total = int(
            await self.db.scalar(select(func.count(CaseNotebookNote.id)).where(*in_case))
            or 0
        )
        return NotebookNotePage(
            items=[self._note_read(note, current_user) for note in page_items],
            next_cursor=page_items[-1].id if has_more and page_items else None,
            has_more=has_more,
            total=total,
        )

    async def create_note(
        self, case_id: uuid.UUID, user: User, data: NotebookNoteWrite
    ) -> NotebookNoteRead:
        note = CaseNotebookNote(
            case_id=case_id,
            author_user_id=user.id,
            title=data.title,
            body=data.body,
        )
        self.db.add(note)
        await self.db.commit()
        return await self._get_note(note.id, user)

    async def update_note(
        self,
        case_id: uuid.UUID,
        note_id: uuid.UUID,
        user: User,
        data: NotebookNoteWrite,
    ) -> NotebookNoteRead:
        note = await self._owned_note(case_id, note_id, user.id)
        note.title = data.title
        note.body = data.body
        await self.db.commit()
        return await self._get_note(note.id, user)

    async def delete_note(
        self, case_id: uuid.UUID, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        note = await self._owned_note(case_id, note_id, user_id)
        await self.db.delete(note)
        await self.db.commit()

    async def list_timeline(
        self, case_id: uuid.UUID, current_user: User
    ) -> list[TimelineEntryRead]:
        entries = list(
            (
                await self.db.execute(
                    select(CaseTimelineEntry)
                    .where(
                        CaseTimelineEntry.case_id == case_id,
                        CaseTimelineEntry.author_user_id == current_user.id,
                    )
                    .options(
                        selectinload(CaseTimelineEntry.author).selectinload(User.profile)
                    )
                    .order_by(CaseTimelineEntry.occurred_on, CaseTimelineEntry.id)
                )
            ).scalars()
        )
        return [self._timeline_read(entry, current_user) for entry in entries]

    async def create_timeline_entry(
        self, case_id: uuid.UUID, user: User, data: TimelineEntryWrite
    ) -> TimelineEntryRead:
        entry = CaseTimelineEntry(
            case_id=case_id,
            author_user_id=user.id,
            occurred_on=data.occurred_on,
            title=data.title,
            body=data.body,
        )
        self.db.add(entry)
        await self.db.commit()
        return await self._get_timeline_entry(entry.id, user)

    async def update_timeline_entry(
        self,
        case_id: uuid.UUID,
        entry_id: uuid.UUID,
        user: User,
        data: TimelineEntryWrite,
    ) -> TimelineEntryRead:
        entry = await self._owned_timeline_entry(case_id, entry_id, user.id)
        entry.occurred_on = data.occurred_on
        entry.title = data.title
        entry.body = data.body
        await self.db.commit()
        return await self._get_timeline_entry(entry.id, user)

    async def delete_timeline_entry(
        self, case_id: uuid.UUID, entry_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        entry = await self._owned_timeline_entry(case_id, entry_id, user_id)
        await self.db.delete(entry)
        await self.db.commit()

    async def _get_note(self, note_id: uuid.UUID, current_user: User) -> NotebookNoteRead:
        note = await self.db.scalar(
            select(CaseNotebookNote)
            .where(CaseNotebookNote.id == note_id)
            .options(selectinload(CaseNotebookNote.author).selectinload(User.profile))
        )
        assert note is not None
        return self._note_read(note, current_user)

    async def _owned_note(
        self, case_id: uuid.UUID, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> CaseNotebookNote:
        note = await self.db.scalar(
            select(CaseNotebookNote).where(
                CaseNotebookNote.id == note_id,
                CaseNotebookNote.case_id == case_id,
                CaseNotebookNote.author_user_id == user_id,
            )
        )
        if note is None:
            raise AppError(404, "note_not_found", "Notebook note was not found")
        return note

    async def _get_timeline_entry(
        self, entry_id: uuid.UUID, current_user: User
    ) -> TimelineEntryRead:
        entry = await self.db.scalar(
            select(CaseTimelineEntry)
            .where(CaseTimelineEntry.id == entry_id)
            .options(selectinload(CaseTimelineEntry.author).selectinload(User.profile))
        )
        assert entry is not None
        return self._timeline_read(entry, current_user)

    async def _owned_timeline_entry(
        self, case_id: uuid.UUID, entry_id: uuid.UUID, user_id: uuid.UUID
    ) -> CaseTimelineEntry:
        entry = await self.db.scalar(
            select(CaseTimelineEntry).where(
                CaseTimelineEntry.id == entry_id,
                CaseTimelineEntry.case_id == case_id,
                CaseTimelineEntry.author_user_id == user_id,
            )
        )
        if entry is None:
            raise AppError(404, "timeline_entry_not_found", "Timeline entry was not found")
        return entry

    @staticmethod
    def _author(user: User) -> ContributorAuthorRead:
        return ContributorAuthorRead(
            id=user.id,
            username=user.username,
            display_name=user.profile.display_name,
        )

    @classmethod
    def _note_read(
        cls, note: CaseNotebookNote, current_user: User
    ) -> NotebookNoteRead:
        return NotebookNoteRead(
            id=note.id,
            case_id=note.case_id,
            title=note.title,
            body=note.body,
            author=cls._author(note.author),
            can_edit=note.author_user_id == current_user.id,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    @classmethod
    def _timeline_read(
        cls, entry: CaseTimelineEntry, current_user: User
    ) -> TimelineEntryRead:
        return TimelineEntryRead(
            id=entry.id,
            case_id=entry.case_id,
            occurred_on=entry.occurred_on,
            title=entry.title,
            body=entry.body,
            author=cls._author(entry.author),
            can_edit=entry.author_user_id == current_user.id,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
