import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cases.models import Case
from app.common.errors import AppError
from app.reels.models import ReelDraft
from app.reels.schemas import ReelDraftCreate, ReelDraftRead, ReelDraftUpdate
from app.users.models import User


class ReelService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, case_id: uuid.UUID) -> list[ReelDraftRead]:
        items = await self.db.scalars(
            select(ReelDraft).where(ReelDraft.case_id == case_id).order_by(ReelDraft.updated_at.desc())
        )
        return [ReelDraftRead.model_validate(item) for item in items]

    async def create(self, case_id: uuid.UUID, user: User, data: ReelDraftCreate) -> ReelDraftRead:
        if await self.db.scalar(select(Case.id).where(Case.id == case_id)) is None:
            raise AppError(404, "case_not_found", "Case was not found")
        item = ReelDraft(
            case_id=case_id,
            created_by_user_id=user.id,
            **data.model_dump(mode="json"),
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return ReelDraftRead.model_validate(item)

    async def update(
        self,
        case_id: uuid.UUID,
        reel_id: uuid.UUID,
        user: User,
        data: ReelDraftUpdate,
    ) -> ReelDraftRead:
        item = await self.db.scalar(
            select(ReelDraft).where(ReelDraft.id == reel_id, ReelDraft.case_id == case_id)
        )
        if item is None:
            raise AppError(404, "reel_not_found", "Reel draft was not found")
        if item.automated:
            raise AppError(409, "automated_reel_read_only", "Automated reel records cannot be edited")
        case_owner_id = await self.db.scalar(select(Case.created_by_user_id).where(Case.id == case_id))
        if item.created_by_user_id != user.id and case_owner_id != user.id and not user.is_admin:
            raise AppError(403, "reel_edit_forbidden", "You cannot edit this reel draft")
        for field, value in data.model_dump(mode="json").items():
            setattr(item, field, value)
        await self.db.commit()
        await self.db.refresh(item)
        return ReelDraftRead.model_validate(item)
