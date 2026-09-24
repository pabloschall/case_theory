import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class MemberRead(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    is_blocked_by_me: bool = False


class ConversationCreate(BaseModel):
    recipient_user_id: uuid.UUID


class MessageCreate(BaseModel):
    body: str = Field(default="", max_length=5000)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def require_content(self) -> "MessageCreate":
        self.body = self.body.strip()
        if not self.body and not self.attachment_ids:
            raise ValueError("Add a message or attach a file")
        return self


class AttachmentRead(BaseModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size: int
    status: str


class AttachmentUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=3, max_length=150)
    file_size: int = Field(gt=0)


class AttachmentUploadTicket(BaseModel):
    attachment: AttachmentRead
    upload_url: str
    upload_method: str
    upload_headers: dict[str, str]


class AttachmentUrl(BaseModel):
    url: str


class MessageRead(BaseModel):
    id: uuid.UUID
    sender: MemberRead
    body: str
    attachments: list[AttachmentRead]
    created_at: datetime


class ConversationSummaryRead(BaseModel):
    id: uuid.UUID
    other_user: MemberRead
    last_message: str | None
    updated_at: datetime


class ConversationPage(BaseModel):
    items: list[ConversationSummaryRead]
    next_cursor: uuid.UUID | None
    has_more: bool
    total: int


class ConversationRead(BaseModel):
    id: uuid.UUID
    other_user: MemberRead
    messages: list[MessageRead]
    last_message: str | None
    updated_at: datetime
    next_cursor: uuid.UUID | None
    has_more: bool
    total_messages: int
