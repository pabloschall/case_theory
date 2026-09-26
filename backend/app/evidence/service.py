import builtins
import hashlib
import uuid
from pathlib import Path
from typing import Literal, cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cases.models import Case, TimelineEvent
from app.common.errors import AppError
from app.config.settings import Settings, get_settings
from app.evidence.models import Evidence, EvidenceComment, TimelineEventEvidence
from app.evidence.schemas import (
    EvidenceCommentAuthor,
    EvidenceCommentCreate,
    EvidenceCommentRead,
    EvidenceRead,
    ExternalEvidenceCreate,
    UploadRequest,
    UploadTicket,
)
from app.people.models import Person, PersonEvidence
from app.progression.service import ProgressionEvent, ProgressionService
from app.storage.base import StorageProvider
from app.users.models import User

ALLOWED_UPLOADS: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".csv": {"text/csv", "text/plain"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
    ".heic": {"image/heic", "image/heif"},
    ".heif": {"image/heic", "image/heif"},
    ".mp3": {"audio/mpeg"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime"},
}


def to_evidence_read(item: Evidence, *, include_details: bool = True, comment_count: int = 0) -> EvidenceRead:
    result = EvidenceRead.model_validate(item).model_copy(update={"comment_count": comment_count})
    if include_details:
        return result
    return result.model_copy(
        update={
            "original_filename": None,
            "mime_type": None,
            "file_size": None,
            "source_url": None,
            "source_id": None,
        }
    )


class EvidenceService:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageProvider,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.settings = settings or get_settings()

    async def list(
        self,
        case_id: uuid.UUID,
        *,
        cursor: uuid.UUID | None = None,
        limit: int = 12,
        include_details: bool = True,
    ) -> tuple[list[EvidenceRead], uuid.UUID | None, bool, int]:
        await self._require_case(case_id)
        statement = select(Evidence).where(Evidence.case_id == case_id, Evidence.moderation_status == "visible")
        if cursor is not None:
            anchor = await self.db.scalar(
                select(Evidence).where(
                    Evidence.id == cursor,
                    Evidence.case_id == case_id,
                    Evidence.moderation_status == "visible",
                )
            )
            if anchor is None:
                raise AppError(400, "invalid_cursor", "Evidence cursor is invalid")
            statement = statement.where(
                or_(
                    Evidence.created_at < anchor.created_at,
                    and_(Evidence.created_at == anchor.created_at, Evidence.id < anchor.id),
                )
            )
        result = await self.db.execute(
            statement.order_by(Evidence.created_at.desc(), Evidence.id.desc()).limit(limit + 1)
        )
        records = list(result.scalars())
        has_more = len(records) > limit
        records = records[:limit]
        total = int(
            await self.db.scalar(
                select(func.count(Evidence.id)).where(
                    Evidence.case_id == case_id, Evidence.moderation_status == "visible"
                )
            )
            or 0
        )
        comment_counts: dict[uuid.UUID, int] = {}
        if records:
            counts = await self.db.execute(
                select(EvidenceComment.evidence_id, func.count(EvidenceComment.id))
                .where(
                    EvidenceComment.evidence_id.in_([item.id for item in records]),
                    EvidenceComment.moderation_status == "visible",
                )
                .group_by(EvidenceComment.evidence_id)
            )
            comment_counts = {evidence_id: int(count) for evidence_id, count in counts.all()}
        items = [
            to_evidence_read(
                item,
                include_details=include_details,
                comment_count=comment_counts.get(item.id, 0),
            )
            for item in records
        ]
        next_cursor = records[-1].id if has_more and records else None
        return items, next_cursor, has_more, total

    async def create_external(self, case_id: uuid.UUID, user: User, data: ExternalEvidenceCreate) -> EvidenceRead:
        await self._require_case(case_id)
        item = Evidence(
            case_id=case_id,
            uploaded_by_user_id=user.id,
            title=data.title,
            description=data.description.strip() if data.description else None,
            evidence_type=data.evidence_type,
            source_url=str(data.url),
            processing_status="available",
        )
        self.db.add(item)
        await self.db.flush()
        await self._link_people(case_id, item.id, data.person_ids, user.id)
        await self.db.commit()
        await self._award_person_links(item, set(data.person_ids))
        if item.description:
            await ProgressionService(self.db, self.settings).award_safely(
                ProgressionEvent(
                    user_id=user.id,
                    event_key=f"external_evidence_added:{item.id}",
                    rule_code="external_evidence_added",
                    resource_type="evidence",
                    resource_id=str(item.id),
                    case_id=case_id,
                )
            )
        await self.db.refresh(item)
        return to_evidence_read(item)

    async def request_upload(self, case_id: uuid.UUID, user: User, data: UploadRequest) -> UploadTicket:
        await self._require_case(case_id)
        filename = Path(data.filename).name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_UPLOADS or data.content_type not in ALLOWED_UPLOADS[suffix]:
            raise AppError(422, "unsupported_file", "This file type is not supported")
        if data.file_size > self.settings.evidence_max_upload_bytes:
            raise AppError(413, "file_too_large", "Evidence files may be up to 25 MB")
        evidence_id = uuid.uuid4()
        object_key = f"cases/{case_id}/evidence/{evidence_id}/{filename}"
        item = Evidence(
            id=evidence_id,
            case_id=case_id,
            uploaded_by_user_id=user.id,
            title=data.title,
            description=data.description.strip() if data.description else None,
            evidence_type=_evidence_type(data.content_type),
            storage_object_key=object_key,
            original_filename=filename,
            mime_type=data.content_type,
            file_size=data.file_size,
        )
        self.db.add(item)
        await self._link_people(case_id, item.id, data.person_ids, user.id)
        await self.db.commit()
        upload_url, method = await self.storage.create_upload_url(object_key, data.content_type)
        return UploadTicket(
            evidence=to_evidence_read(item),
            upload_url=upload_url,
            upload_method=cast(Literal["POST", "PUT"], method),
            upload_headers={"Content-Type": data.content_type},
        )

    async def complete_upload(self, case_id: uuid.UUID, evidence_id: uuid.UUID) -> EvidenceRead:
        item = await self._get(case_id, evidence_id)
        if item.storage_object_key is None:
            raise AppError(409, "not_an_upload", "This evidence item is an external link")
        if item.processing_status == "available":
            return to_evidence_read(item)
        metadata = await self.storage.metadata(item.storage_object_key)
        if metadata.size <= 0 or metadata.size > self.settings.evidence_max_upload_bytes:
            await self.storage.delete(item.storage_object_key)
            item.processing_status = "rejected"
            await self.db.commit()
            raise AppError(422, "invalid_upload", "The uploaded file size is invalid")
        content = await self.storage.read(item.storage_object_key)
        detected_type = _detect_content_type(content, item.original_filename or "")
        suffix = Path(item.original_filename or "").suffix.lower()
        if detected_type is None or detected_type not in ALLOWED_UPLOADS.get(suffix, set()):
            await self.storage.delete(item.storage_object_key)
            item.processing_status = "rejected"
            await self.db.commit()
            raise AppError(422, "invalid_upload", "The file contents do not match its extension")
        item.mime_type = detected_type
        item.file_size = len(content)
        item.sha256_hash = hashlib.sha256(content).hexdigest()
        item.processing_status = "available"
        await self.db.commit()
        await ProgressionService(self.db, self.settings).award_safely(
            ProgressionEvent(
                user_id=item.uploaded_by_user_id,
                event_key=f"evidence_upload_completed:{item.id}",
                rule_code="evidence_upload_completed",
                resource_type="evidence",
                resource_id=str(item.id),
                case_id=case_id,
            )
        )
        person_ids = set(
            await self.db.scalars(
                select(PersonEvidence.person_id).where(PersonEvidence.evidence_id == item.id)
            )
        )
        await self._award_person_links(item, person_ids)
        return to_evidence_read(item)

    async def download_url(self, case_id: uuid.UUID, evidence_id: uuid.UUID) -> str:
        item = await self._get(case_id, evidence_id)
        if item.processing_status != "available" or item.storage_object_key is None:
            raise AppError(409, "evidence_unavailable", "This evidence file is not available")
        return await self.storage.create_download_url(item.storage_object_key)

    async def attach_to_timeline(
        self,
        case_id: uuid.UUID,
        timeline_event_id: uuid.UUID,
        evidence_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        event = await self.db.scalar(
            select(TimelineEvent).where(
                TimelineEvent.id == timeline_event_id,
                TimelineEvent.case_id == case_id,
            )
        )
        if event is None:
            raise AppError(404, "timeline_event_not_found", "Timeline event was not found")
        await self._get(case_id, evidence_id)
        exists = await self.db.scalar(
            select(TimelineEventEvidence.id).where(
                TimelineEventEvidence.timeline_event_id == timeline_event_id,
                TimelineEventEvidence.evidence_id == evidence_id,
            )
        )
        if exists is None:
            self.db.add(
                TimelineEventEvidence(
                    timeline_event_id=timeline_event_id,
                    evidence_id=evidence_id,
                    created_by_user_id=user_id,
                )
            )
            await self.db.commit()

    async def list_comments(
        self,
        case_id: uuid.UUID,
        evidence_id: uuid.UUID,
        user: User | None,
        *,
        cursor: uuid.UUID | None = None,
        limit: int = 20,
    ) -> tuple[builtins.list[EvidenceCommentRead], uuid.UUID | None, bool, int]:
        await self._get(case_id, evidence_id)
        statement = (
            select(EvidenceComment)
            .where(
                EvidenceComment.evidence_id == evidence_id,
                EvidenceComment.moderation_status == "visible",
            )
            .options(selectinload(EvidenceComment.author).selectinload(User.profile))
        )
        if cursor is not None:
            anchor = await self.db.scalar(
                select(EvidenceComment).where(
                    EvidenceComment.id == cursor,
                    EvidenceComment.evidence_id == evidence_id,
                    EvidenceComment.moderation_status == "visible",
                )
            )
            if anchor is None:
                raise AppError(400, "invalid_cursor", "Evidence comment cursor is invalid")
            statement = statement.where(
                or_(
                    EvidenceComment.created_at < anchor.created_at,
                    and_(
                        EvidenceComment.created_at == anchor.created_at,
                        EvidenceComment.id < anchor.id,
                    ),
                )
            )
        result = await self.db.scalars(
            statement.order_by(EvidenceComment.created_at.desc(), EvidenceComment.id.desc()).limit(limit + 1)
        )
        records = list(result)
        has_more = len(records) > limit
        records = records[:limit]
        total = int(
            await self.db.scalar(
                select(func.count(EvidenceComment.id)).where(
                    EvidenceComment.evidence_id == evidence_id,
                    EvidenceComment.moderation_status == "visible",
                )
            )
            or 0
        )
        owner_id = await self._case_owner(case_id)
        items = [self._comment_read(item, user, owner_id) for item in records]
        next_cursor = records[-1].id if has_more and records else None
        return items, next_cursor, has_more, total

    async def create_comment(
        self,
        case_id: uuid.UUID,
        evidence_id: uuid.UUID,
        user: User,
        data: EvidenceCommentCreate,
    ) -> EvidenceCommentRead:
        await self._get(case_id, evidence_id)
        comment = EvidenceComment(
            evidence_id=evidence_id,
            author_user_id=user.id,
            body=data.body,
        )
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return EvidenceCommentRead(
            id=comment.id,
            body=comment.body,
            author=EvidenceCommentAuthor(
                id=user.id,
                username=user.username,
                display_name=user.profile.display_name,
            ),
            can_delete=True,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )

    async def delete_comment(
        self,
        case_id: uuid.UUID,
        evidence_id: uuid.UUID,
        comment_id: uuid.UUID,
        user: User,
    ) -> None:
        await self._get(case_id, evidence_id)
        comment = await self.db.scalar(
            select(EvidenceComment).where(
                EvidenceComment.id == comment_id,
                EvidenceComment.evidence_id == evidence_id,
            )
        )
        if comment is None:
            raise AppError(404, "evidence_comment_not_found", "Evidence comment was not found")
        owner_id = await self._case_owner(case_id)
        if not (user.is_admin or user.id in {comment.author_user_id, owner_id}):
            raise AppError(403, "comment_delete_forbidden", "You cannot delete this comment")
        await self.db.delete(comment)
        await self.db.commit()

    async def _get(self, case_id: uuid.UUID, evidence_id: uuid.UUID) -> Evidence:
        item = await self.db.scalar(
            select(Evidence).where(
                Evidence.id == evidence_id,
                Evidence.case_id == case_id,
                Evidence.moderation_status == "visible",
            )
        )
        if item is None:
            raise AppError(404, "evidence_not_found", "Evidence was not found")
        return item

    async def _require_case(self, case_id: uuid.UUID) -> None:
        if await self.db.scalar(select(Case.id).where(Case.id == case_id)) is None:
            raise AppError(404, "case_not_found", "Case was not found")

    async def _link_people(
        self,
        case_id: uuid.UUID,
        evidence_id: uuid.UUID,
        person_ids: builtins.list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> None:
        if not person_ids:
            return
        unique_ids = set(person_ids)
        people = list(
            (
                await self.db.execute(
                    select(Person).where(
                        Person.case_id == case_id,
                        Person.id.in_(unique_ids),
                    )
                )
            ).scalars()
        )
        if len(people) != len(unique_ids):
            raise AppError(
                422,
                "invalid_people",
                "One or more people do not belong to this case",
            )
        self.db.add_all(
            [
                PersonEvidence(
                    person_id=person.id,
                    evidence_id=evidence_id,
                    created_by_user_id=user_id,
                )
                for person in people
            ]
        )

    async def _award_person_links(self, item: Evidence, person_ids: set[uuid.UUID]) -> None:
        service = ProgressionService(self.db, self.settings)
        for person_id in person_ids:
            await service.award_safely(
                ProgressionEvent(
                    user_id=item.uploaded_by_user_id,
                    event_key=f"evidence_person_linked:{item.id}:{person_id}",
                    rule_code="evidence_person_linked",
                    resource_type="evidence_person_link",
                    resource_id=f"{item.id}:{person_id}",
                    case_id=item.case_id,
                )
            )

    async def _case_owner(self, case_id: uuid.UUID) -> uuid.UUID:
        owner_id = await self.db.scalar(select(Case.created_by_user_id).where(Case.id == case_id))
        if owner_id is None:
            raise AppError(404, "case_not_found", "Case was not found")
        return owner_id

    @staticmethod
    def _comment_read(
        comment: EvidenceComment,
        user: User | None,
        owner_id: uuid.UUID,
    ) -> EvidenceCommentRead:
        return EvidenceCommentRead(
            id=comment.id,
            body=comment.body,
            author=EvidenceCommentAuthor(
                id=comment.author.id,
                username=comment.author.username,
                display_name=comment.author.profile.display_name,
            ),
            can_delete=bool(user and (user.is_admin or user.id in {comment.author_user_id, owner_id})),
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )


def _evidence_type(content_type: str) -> str:
    prefix = content_type.split("/", maxsplit=1)[0]
    return prefix if prefix in {"image", "video", "audio"} else "document"


def _detect_content_type(content: bytes, filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"RIFF") and content[8:12] == b"WAVE":
        return "audio/wav"
    if content.startswith(b"PK\x03\x04") and suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if len(content) > 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if suffix in {".heic", ".heif"} and brand in {
            b"heic",
            b"heix",
            b"hevc",
            b"hevx",
            b"mif1",
            b"msf1",
        }:
            return "image/heif" if suffix == ".heif" else "image/heic"
        if suffix == ".mp4":
            return "video/mp4"
        if suffix == ".mov":
            return "video/quicktime"
    if (content.startswith(b"ID3") or content[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}) and suffix == ".mp3":
        return "audio/mpeg"
    if suffix in {".txt", ".csv"}:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return "text/csv" if suffix == ".csv" else "text/plain"
    return None
