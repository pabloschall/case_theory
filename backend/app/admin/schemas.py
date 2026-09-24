import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminUserRead(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    display_name: str
    is_active: bool
    moderation_status: str
    is_verified: bool
    is_admin: bool
    tier_level: int
    plan_code: str
    plan_name: str
    case_count: int
    created_at: datetime


class AdminUserPage(BaseModel):
    items: list[AdminUserRead]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class AdminTierUpdate(BaseModel):
    tier_level: Literal[0, 1, 2, 3]


class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("Password must include a letter and a number")
        return value


class AdminCaseRead(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    privacy: str
    ai_research_status: str
    cover_image_url: str | None
    owner_id: uuid.UUID
    owner_email: str
    owner_username: str
    owner_display_name: str
    created_at: datetime
    updated_at: datetime


class AdminCasePage(BaseModel):
    items: list[AdminCaseRead]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool
