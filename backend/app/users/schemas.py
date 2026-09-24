import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    is_verified: bool
    plan_code: str
    tier_level: int
    permissions: list[str]
    ai_cases_remaining: int | None
    ai_limit_period: str
    ai_resets_at: datetime | None
    weekly_cases_remaining: int | None
    weekly_case_limit: int
    weekly_cases_reset_at: datetime | None
    created_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_]+$")
    bio: str = Field(default="", max_length=1000)


class AvatarUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=3, max_length=150)
    file_size: int = Field(gt=0)


class AvatarUploadTicket(BaseModel):
    upload_id: uuid.UUID
    upload_url: str
    upload_method: str
    upload_headers: dict[str, str]


class BlockState(BaseModel):
    is_blocked: bool
