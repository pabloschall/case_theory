import uuid
from datetime import datetime

from pydantic import BaseModel


class InvitationCreate(BaseModel):
    role: str = "contributor"


class InvitationCreated(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    case_title: str
    inviter_name: str
    role: str
    invite_url: str
    message: str
    expires_at: datetime


class InvitationPreview(BaseModel):
    case_id: uuid.UUID
    case_title: str
    inviter_name: str
    role: str
    expires_at: datetime
    is_available: bool
    requires_account: bool = True


class InvitationAccepted(BaseModel):
    case_id: uuid.UUID
    message: str
