import uuid
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppError
from app.config.settings import Settings, get_settings
from app.evidence.service import _detect_content_type
from app.storage.base import StorageProvider
from app.users.models import User, UserAvatarUpload, UserBlock
from app.users.schemas import AvatarUploadRequest, AvatarUploadTicket, ProfileUpdate

AVATAR_TYPES: dict[str, set[str]] = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".heic": {"image/heic", "image/heif"},
    ".heif": {"image/heic", "image/heif"},
}


class UserService:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.settings = settings or get_settings()

    async def update_profile(self, user: User, data: ProfileUpdate) -> User:
        user.username = data.username.strip().lower()
        user.profile.display_name = data.display_name.strip()
        user.profile.bio = data.bio.strip() or None
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AppError(409, "username_taken", "That username is already in use") from exc
        return user

    async def request_avatar(
        self, user: User, data: AvatarUploadRequest
    ) -> AvatarUploadTicket:
        if self.storage is None:
            raise RuntimeError("Storage provider is required")
        filename = Path(data.filename).name
        suffix = Path(filename).suffix.lower()
        if suffix not in AVATAR_TYPES or data.content_type not in AVATAR_TYPES[suffix]:
            raise AppError(422, "unsupported_avatar", "Choose a JPEG, PNG, WebP, or HEIC image")
        if data.file_size > self.settings.avatar_max_upload_bytes:
            raise AppError(413, "avatar_too_large", "Profile pictures may be up to 8 MB")
        upload_id = uuid.uuid4()
        object_key = f"users/{user.id}/avatars/{upload_id}/{filename}"
        upload = UserAvatarUpload(
            id=upload_id,
            user_id=user.id,
            storage_object_key=object_key,
            original_filename=filename,
            mime_type=data.content_type,
            file_size=data.file_size,
        )
        self.db.add(upload)
        await self.db.commit()
        upload_url, method = await self.storage.create_upload_url(object_key, data.content_type)
        return AvatarUploadTicket(
            upload_id=upload.id,
            upload_url=upload_url,
            upload_method=method,
            upload_headers={"Content-Type": data.content_type},
        )

    async def complete_avatar(self, user: User, upload_id: uuid.UUID) -> User:
        if self.storage is None:
            raise RuntimeError("Storage provider is required")
        upload = await self.db.scalar(
            select(UserAvatarUpload).where(
                UserAvatarUpload.id == upload_id,
                UserAvatarUpload.user_id == user.id,
                UserAvatarUpload.status == "pending",
            )
        )
        if upload is None:
            raise AppError(404, "avatar_upload_not_found", "Profile picture upload was not found")
        metadata = await self.storage.metadata(upload.storage_object_key)
        if metadata.size <= 0 or metadata.size > self.settings.avatar_max_upload_bytes:
            await self._reject_upload(upload)
            raise AppError(422, "invalid_avatar", "The uploaded image size is invalid")
        content = await self.storage.read(upload.storage_object_key)
        suffix = Path(upload.original_filename).suffix.lower()
        detected = _detect_content_type(content, upload.original_filename)
        if detected is None or detected not in AVATAR_TYPES.get(suffix, set()):
            await self._reject_upload(upload)
            raise AppError(422, "invalid_avatar", "The image contents do not match its file type")
        previous_key = user.profile.avatar_object_key
        upload.status = "available"
        upload.mime_type = detected
        upload.file_size = len(content)
        user.profile.avatar_object_key = upload.storage_object_key
        user.profile.avatar_url = f"/api/v1/users/{user.id}/avatar"
        await self.db.commit()
        if previous_key and previous_key != upload.storage_object_key:
            await self.storage.delete(previous_key)
        return user

    async def avatar_object_key(self, user_id: uuid.UUID) -> str:
        user = await self._user(user_id)
        if not user.profile.avatar_object_key:
            raise AppError(404, "avatar_not_found", "Profile picture was not found")
        return user.profile.avatar_object_key

    async def block(self, blocker: User, blocked_user_id: uuid.UUID) -> None:
        if blocker.id == blocked_user_id:
            raise AppError(422, "cannot_block_self", "You cannot block yourself")
        await self._user(blocked_user_id)
        existing = await self.db.scalar(
            select(UserBlock).where(
                UserBlock.blocker_user_id == blocker.id,
                UserBlock.blocked_user_id == blocked_user_id,
            )
        )
        if existing is None:
            self.db.add(
                UserBlock(blocker_user_id=blocker.id, blocked_user_id=blocked_user_id)
            )
            await self.db.commit()

    async def unblock(self, blocker: User, blocked_user_id: uuid.UUID) -> None:
        item = await self.db.scalar(
            select(UserBlock).where(
                UserBlock.blocker_user_id == blocker.id,
                UserBlock.blocked_user_id == blocked_user_id,
            )
        )
        if item is not None:
            await self.db.delete(item)
            await self.db.commit()

    async def blocked_users(self, current: User) -> list[User]:
        result = await self.db.scalars(
            select(User)
            .join(UserBlock, UserBlock.blocked_user_id == User.id)
            .where(UserBlock.blocker_user_id == current.id)
            .options(selectinload(User.profile))
            .order_by(UserBlock.created_at.desc())
        )
        return list(result)

    async def is_blocked_by(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        return (
            await self.db.scalar(
                select(UserBlock.id).where(
                    UserBlock.blocker_user_id == blocker_id,
                    UserBlock.blocked_user_id == blocked_id,
                )
            )
            is not None
        )

    async def messaging_blocked(self, first_id: uuid.UUID, second_id: uuid.UUID) -> bool:
        return (
            await self.db.scalar(
                select(UserBlock.id).where(
                    or_(
                        UserBlock.blocker_user_id == first_id,
                        UserBlock.blocker_user_id == second_id,
                    ),
                    or_(
                        UserBlock.blocked_user_id == first_id,
                        UserBlock.blocked_user_id == second_id,
                    ),
                    UserBlock.blocker_user_id != UserBlock.blocked_user_id,
                )
            )
            is not None
        )

    async def _reject_upload(self, upload: UserAvatarUpload) -> None:
        assert self.storage is not None
        await self.storage.delete(upload.storage_object_key)
        upload.status = "rejected"
        await self.db.commit()

    async def _user(self, user_id: uuid.UUID) -> User:
        user = await self.db.scalar(
            select(User)
            .where(User.id == user_id, User.is_active.is_(True))
            .options(selectinload(User.profile))
        )
        if user is None:
            raise AppError(404, "user_not_found", "Member was not found")
        return user
