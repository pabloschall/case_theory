import hashlib
import uuid
from pathlib import Path

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.config.settings import Settings, get_settings
from app.evidence.service import ALLOWED_UPLOADS, _detect_content_type
from app.messaging.models import DirectConversation, DirectMessage, MessageAttachment
from app.messaging.schemas import (
    AttachmentRead,
    AttachmentUploadRequest,
    AttachmentUploadTicket,
    ConversationRead,
    ConversationSummaryRead,
    MemberRead,
    MessageCreate,
    MessageRead,
)
from app.storage.base import StorageProvider
from app.users.models import User
from app.users.service import UserService


def member_read(user: User, *, is_blocked_by_me: bool = False) -> MemberRead:
    return MemberRead(
        id=user.id,
        username=user.username,
        display_name=user.profile.display_name,
        bio=user.profile.bio,
        avatar_url=user.profile.avatar_url,
        is_blocked_by_me=is_blocked_by_me,
    )


def attachment_read(item: MessageAttachment) -> AttachmentRead:
    return AttachmentRead(
        id=item.id,
        original_filename=item.original_filename,
        mime_type=item.mime_type,
        file_size=item.file_size,
        status=item.status,
    )


class MessagingService:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.settings = settings or get_settings()

    async def profile(self, user_id: uuid.UUID, current: User) -> MemberRead:
        return member_read(
            await self._user(user_id),
            is_blocked_by_me=await UserService(self.db).is_blocked_by(current.id, user_id),
        )

    async def open(self, current: User, recipient_id: uuid.UUID) -> ConversationRead:
        if recipient_id == current.id:
            raise AppError(422, "cannot_message_self", "You cannot message yourself")
        recipient = await self._user(recipient_id)
        await self._require_messaging_allowed(current.id, recipient.id)
        first, second = sorted((current.id, recipient.id), key=str)
        conversation = await self.db.scalar(
            select(DirectConversation).where(
                DirectConversation.user_one_id == first,
                DirectConversation.user_two_id == second,
            )
        )
        if conversation is None:
            conversation = DirectConversation(user_one_id=first, user_two_id=second)
            self.db.add(conversation)
            await self.db.commit()
        return await self.get(conversation.id, current)

    async def list_conversations(
        self,
        current: User,
        *,
        cursor: uuid.UUID | None = None,
        limit: int = 20,
    ) -> tuple[list[ConversationSummaryRead], uuid.UUID | None, bool, int]:
        participant = self._participant_condition(current.id)
        statement = self._participants().where(participant)
        if cursor is not None:
            anchor = await self.db.scalar(
                select(DirectConversation).where(
                    DirectConversation.id == cursor,
                    participant,
                )
            )
            if anchor is None:
                raise AppError(400, "invalid_cursor", "Conversation cursor is invalid")
            statement = statement.where(
                or_(
                    DirectConversation.updated_at < anchor.updated_at,
                    and_(
                        DirectConversation.updated_at == anchor.updated_at,
                        DirectConversation.id < anchor.id,
                    ),
                )
            )
        result = await self.db.scalars(
            statement.order_by(
                DirectConversation.updated_at.desc(), DirectConversation.id.desc()
            ).limit(limit + 1)
        )
        records = list(result.unique())
        has_more = len(records) > limit
        records = records[:limit]
        latest_messages = await self._latest_message_bodies([item.id for item in records])
        unread_ids = await self._unread_conversation_ids(current.id, [item.id for item in records])
        total = int(
            await self.db.scalar(
                select(func.count(DirectConversation.id)).where(participant)
            )
            or 0
        )
        items = [
            self._summary(item, current.id, latest_messages.get(item.id), item.id in unread_ids)
            for item in records
        ]
        next_cursor = records[-1].id if has_more and records else None
        return items, next_cursor, has_more, total

    async def has_unread(self, current: User) -> bool:
        statement = (
            select(DirectMessage.id)
            .join(DirectConversation, DirectMessage.conversation_id == DirectConversation.id)
            .where(self._unread_condition(current.id))
            .limit(1)
        )
        return await self.db.scalar(statement) is not None

    async def mark_read(
        self, conversation_id: uuid.UUID, message_id: uuid.UUID, current: User
    ) -> None:
        conversation = await self._conversation(conversation_id, current.id)
        message = await self.db.scalar(
            select(DirectMessage).where(
                DirectMessage.id == message_id,
                DirectMessage.conversation_id == conversation_id,
            )
        )
        if message is None:
            raise AppError(404, "message_not_found", "Message was not found")
        field = "user_one_read_at" if conversation.user_one_id == current.id else "user_two_read_at"
        previous = getattr(conversation, field)
        if previous is None or previous < message.created_at:
            setattr(conversation, field, message.created_at)
            conversation.updated_at = conversation.updated_at
            await self.db.commit()

    async def _unread_conversation_ids(
        self, user_id: uuid.UUID, conversation_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not conversation_ids:
            return set()
        result = await self.db.scalars(
            select(DirectMessage.conversation_id)
            .join(DirectConversation, DirectMessage.conversation_id == DirectConversation.id)
            .where(
                DirectConversation.id.in_(conversation_ids),
                self._unread_condition(user_id),
            )
            .distinct()
        )
        return set(result)

    @staticmethod
    def _unread_condition(user_id: uuid.UUID) -> ColumnElement[bool]:
        return and_(
            DirectMessage.sender_user_id != user_id,
            or_(
                and_(
                    DirectConversation.user_one_id == user_id,
                    or_(
                        DirectConversation.user_one_read_at.is_(None),
                        DirectMessage.created_at > DirectConversation.user_one_read_at,
                    ),
                ),
                and_(
                    DirectConversation.user_two_id == user_id,
                    or_(
                        DirectConversation.user_two_read_at.is_(None),
                        DirectMessage.created_at > DirectConversation.user_two_read_at,
                    ),
                ),
            ),
        )

    async def get(
        self,
        conversation_id: uuid.UUID,
        current: User,
        *,
        cursor: uuid.UUID | None = None,
        limit: int = 30,
    ) -> ConversationRead:
        conversation = await self.db.scalar(
            self._participants().where(
                DirectConversation.id == conversation_id,
                self._participant_condition(current.id),
            )
        )
        if conversation is None:
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        statement = self._messages().where(
            DirectMessage.conversation_id == conversation.id
        )
        if cursor is not None:
            anchor = await self.db.scalar(
                select(DirectMessage).where(
                    DirectMessage.id == cursor,
                    DirectMessage.conversation_id == conversation.id,
                )
            )
            if anchor is None:
                raise AppError(400, "invalid_cursor", "Message cursor is invalid")
            statement = statement.where(
                or_(
                    DirectMessage.created_at < anchor.created_at,
                    and_(
                        DirectMessage.created_at == anchor.created_at,
                        DirectMessage.id < anchor.id,
                    ),
                )
            )
        result = await self.db.scalars(
            statement.order_by(DirectMessage.created_at.desc(), DirectMessage.id.desc())
            .limit(limit + 1)
        )
        records = list(result.unique())
        has_more = len(records) > limit
        records = records[:limit]
        total_messages = int(
            await self.db.scalar(
                select(func.count(DirectMessage.id)).where(
                    DirectMessage.conversation_id == conversation.id
                )
            )
            or 0
        )
        latest_messages = await self._latest_message_bodies([conversation.id])
        chronological = list(reversed(records))
        return ConversationRead(
            **self._summary(
                conversation,
                current.id,
                latest_messages.get(conversation.id),
            ).model_dump(),
            messages=[self._message_read(item) for item in chronological],
            next_cursor=records[-1].id if has_more and records else None,
            has_more=has_more,
            total_messages=total_messages,
        )

    async def send(
        self, conversation_id: uuid.UUID, current: User, data: MessageCreate
    ) -> MessageRead:
        conversation = await self._conversation(conversation_id, current.id)
        await self._require_messaging_allowed(
            conversation.user_one_id, conversation.user_two_id
        )
        attachments: list[MessageAttachment] = []
        if data.attachment_ids:
            unique_ids = set(data.attachment_ids)
            attachments = list(
                await self.db.scalars(
                    select(MessageAttachment).where(
                        MessageAttachment.id.in_(unique_ids),
                        MessageAttachment.conversation_id == conversation.id,
                        MessageAttachment.uploaded_by_user_id == current.id,
                        MessageAttachment.message_id.is_(None),
                        MessageAttachment.status == "available",
                    )
                )
            )
            if len(attachments) != len(unique_ids):
                raise AppError(422, "attachment_unavailable", "One or more files are unavailable")
        message = DirectMessage(
            conversation_id=conversation.id,
            sender_user_id=current.id,
            body=data.body,
        )
        self.db.add(message)
        await self.db.flush()
        if conversation.user_one_id == current.id:
            conversation.user_one_read_at = message.created_at
        else:
            conversation.user_two_read_at = message.created_at
        for attachment in attachments:
            attachment.message_id = message.id
        conversation.updated_at = utc_now()
        await self.db.commit()
        created = await self.db.scalar(
            self._messages().where(DirectMessage.id == message.id)
        )
        if created is None:
            raise AppError(500, "message_unavailable", "Message could not be loaded")
        return self._message_read(created)

    async def request_attachment(
        self,
        conversation_id: uuid.UUID,
        current: User,
        data: AttachmentUploadRequest,
    ) -> AttachmentUploadTicket:
        conversation = await self._conversation(conversation_id, current.id)
        await self._require_messaging_allowed(
            conversation.user_one_id, conversation.user_two_id
        )
        if self.storage is None:
            raise RuntimeError("Storage provider is required")
        filename = Path(data.filename).name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_UPLOADS or data.content_type not in ALLOWED_UPLOADS[suffix]:
            raise AppError(422, "unsupported_file", "This file type is not supported")
        if data.file_size > self.settings.evidence_max_upload_bytes:
            raise AppError(413, "file_too_large", "Message files may be up to 25 MB")
        attachment_id = uuid.uuid4()
        object_key = f"messages/{conversation_id}/{attachment_id}/{filename}"
        attachment = MessageAttachment(
            id=attachment_id,
            conversation_id=conversation_id,
            uploaded_by_user_id=current.id,
            storage_object_key=object_key,
            original_filename=filename,
            mime_type=data.content_type,
            file_size=data.file_size,
        )
        self.db.add(attachment)
        await self.db.commit()
        upload_url, method = await self.storage.create_upload_url(object_key, data.content_type)
        return AttachmentUploadTicket(
            attachment=attachment_read(attachment),
            upload_url=upload_url,
            upload_method=method,
            upload_headers={"Content-Type": data.content_type},
        )

    async def complete_attachment(
        self, conversation_id: uuid.UUID, attachment_id: uuid.UUID, current: User
    ) -> AttachmentRead:
        await self._conversation(conversation_id, current.id)
        if self.storage is None:
            raise RuntimeError("Storage provider is required")
        attachment = await self._attachment(conversation_id, attachment_id)
        if attachment.uploaded_by_user_id != current.id or attachment.message_id is not None:
            raise AppError(404, "attachment_not_found", "Attachment was not found")
        metadata = await self.storage.metadata(attachment.storage_object_key)
        if metadata.size <= 0 or metadata.size > self.settings.evidence_max_upload_bytes:
            await self.storage.delete(attachment.storage_object_key)
            attachment.status = "rejected"
            await self.db.commit()
            raise AppError(422, "invalid_upload", "The uploaded file size is invalid")
        content = await self.storage.read(attachment.storage_object_key)
        detected = _detect_content_type(content, attachment.original_filename)
        suffix = Path(attachment.original_filename).suffix.lower()
        if detected is None or detected not in ALLOWED_UPLOADS.get(suffix, set()):
            await self.storage.delete(attachment.storage_object_key)
            attachment.status = "rejected"
            await self.db.commit()
            raise AppError(422, "invalid_upload", "The file contents do not match its extension")
        attachment.mime_type = detected
        attachment.file_size = len(content)
        attachment.sha256_hash = hashlib.sha256(content).hexdigest()
        attachment.status = "available"
        await self.db.commit()
        return attachment_read(attachment)

    async def attachment_url(
        self, conversation_id: uuid.UUID, attachment_id: uuid.UUID, current: User
    ) -> str:
        await self._conversation(conversation_id, current.id)
        if self.storage is None:
            raise RuntimeError("Storage provider is required")
        attachment = await self._attachment(conversation_id, attachment_id)
        if attachment.status != "available" or attachment.message_id is None:
            raise AppError(409, "attachment_unavailable", "Attachment is not available")
        return await self.storage.create_download_url(attachment.storage_object_key)

    async def _attachment(
        self, conversation_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> MessageAttachment:
        attachment = await self.db.scalar(
            select(MessageAttachment).where(
                MessageAttachment.id == attachment_id,
                MessageAttachment.conversation_id == conversation_id,
            )
        )
        if attachment is None:
            raise AppError(404, "attachment_not_found", "Attachment was not found")
        return attachment

    async def _conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> DirectConversation:
        conversation = await self.db.scalar(
            select(DirectConversation).where(
                DirectConversation.id == conversation_id,
                self._participant_condition(user_id),
            )
        )
        if conversation is None:
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        return conversation

    @staticmethod
    def _participant_condition(user_id: uuid.UUID) -> ColumnElement[bool]:
        return or_(
            DirectConversation.user_one_id == user_id,
            DirectConversation.user_two_id == user_id,
        )

    async def _user(self, user_id: uuid.UUID) -> User:
        user = await self.db.scalar(
            select(User)
            .where(User.id == user_id, User.is_active.is_(True))
            .options(selectinload(User.profile))
        )
        if user is None:
            raise AppError(404, "user_not_found", "Member was not found")
        return user

    async def _require_messaging_allowed(
        self, first_id: uuid.UUID, second_id: uuid.UUID
    ) -> None:
        if await UserService(self.db).messaging_blocked(first_id, second_id):
            raise AppError(403, "messaging_blocked", "Messaging is unavailable for this member")

    def _participants(self) -> Select[tuple[DirectConversation]]:
        return select(DirectConversation).options(
            selectinload(DirectConversation.user_one).selectinload(User.profile),
            selectinload(DirectConversation.user_two).selectinload(User.profile),
        )

    def _messages(self) -> Select[tuple[DirectMessage]]:
        return select(DirectMessage).options(
            selectinload(DirectMessage.sender).selectinload(User.profile),
            selectinload(DirectMessage.attachments),
        )

    async def _latest_message_bodies(
        self, conversation_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        if not conversation_ids:
            return {}
        rank = func.row_number().over(
            partition_by=DirectMessage.conversation_id,
            order_by=(DirectMessage.created_at.desc(), DirectMessage.id.desc()),
        ).label("message_rank")
        ranked = (
            select(
                DirectMessage.conversation_id.label("conversation_id"),
                DirectMessage.body.label("body"),
                rank,
            )
            .where(DirectMessage.conversation_id.in_(conversation_ids))
            .subquery()
        )
        result = await self.db.execute(
            select(ranked.c.conversation_id, ranked.c.body).where(
                ranked.c.message_rank == 1
            )
        )
        return {conversation_id: body for conversation_id, body in result.all()}

    def _summary(
        self,
        conversation: DirectConversation,
        current_user_id: uuid.UUID,
        last_message: str | None,
        has_unread: bool = False,
    ) -> ConversationSummaryRead:
        other = (
            conversation.user_two
            if conversation.user_one_id == current_user_id
            else conversation.user_one
        )
        return ConversationSummaryRead(
            id=conversation.id,
            other_user=member_read(other),
            last_message=last_message,
            updated_at=conversation.updated_at,
            has_unread=has_unread,
        )

    def _message_read(self, item: DirectMessage) -> MessageRead:
        return MessageRead(
            id=item.id,
            sender=member_read(item.sender),
            body=item.body,
            attachments=[attachment_read(value) for value in item.attachments],
            created_at=item.created_at,
        )
