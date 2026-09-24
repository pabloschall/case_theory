import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_csrf
from app.db.session import get_db
from app.messaging.schemas import (
    AttachmentRead,
    AttachmentUploadRequest,
    AttachmentUploadTicket,
    AttachmentUrl,
    ConversationCreate,
    ConversationPage,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.messaging.service import MessagingService
from app.storage.base import StorageProvider
from app.storage.provider import get_storage_provider
from app.subscriptions.dependencies import require_permission
from app.users.models import User

router = APIRouter(
    prefix="/messages",
    tags=["messaging"],
    dependencies=[Depends(require_permission("messaging.use", required_tier=2))],
)


@router.get("/conversations", response_model=ConversationPage)
async def conversations(
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ConversationPage:
    items, next_cursor, has_more, total = await MessagingService(db).list_conversations(
        user, cursor=cursor, limit=limit
    )
    return ConversationPage(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total=total,
    )


@router.post(
    "/conversations",
    response_model=ConversationRead,
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
async def open_conversation(
    data: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationRead:
    return await MessagingService(db).open(user, data.recipient_user_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
async def conversation(
    conversation_id: uuid.UUID,
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationRead:
    return await MessagingService(db).get(
        conversation_id, user, cursor=cursor, limit=limit
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    dependencies=[Depends(verify_csrf)],
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    return await MessagingService(db).send(conversation_id, user, data)


@router.post(
    "/conversations/{conversation_id}/attachments",
    response_model=AttachmentUploadTicket,
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
async def request_attachment(
    conversation_id: uuid.UUID,
    data: AttachmentUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> AttachmentUploadTicket:
    return await MessagingService(db, storage).request_attachment(conversation_id, user, data)


@router.post(
    "/conversations/{conversation_id}/attachments/{attachment_id}/complete",
    response_model=AttachmentRead,
    dependencies=[Depends(verify_csrf)],
)
async def complete_attachment(
    conversation_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> AttachmentRead:
    return await MessagingService(db, storage).complete_attachment(
        conversation_id, attachment_id, user
    )


@router.get(
    "/conversations/{conversation_id}/attachments/{attachment_id}/url",
    response_model=AttachmentUrl,
)
async def attachment_url(
    conversation_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> AttachmentUrl:
    return AttachmentUrl(
        url=await MessagingService(db, storage).attachment_url(
            conversation_id, attachment_id, user
        )
    )
