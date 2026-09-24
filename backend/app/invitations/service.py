import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cases.models import Case, CaseFollower, CaseMember
from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.config.settings import Settings
from app.invitations.models import CaseInvitation
from app.invitations.schemas import InvitationAccepted, InvitationCreated, InvitationPreview
from app.subscriptions.permissions import PermissionService
from app.users.models import User


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InvitationService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def create(self, case_id: uuid.UUID, user: User, role: str) -> InvitationCreated:
        if role != "contributor":
            raise AppError(422, "invalid_invitation_role", "Only contributor invitations are supported")
        case = await self.db.scalar(select(Case).where(Case.id == case_id))
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        member = await self.db.scalar(
            select(CaseMember.id).where(
                CaseMember.case_id == case.id,
                CaseMember.user_id == user.id,
            )
        )
        can_access = (
            case.privacy == "public"
            or case.created_by_user_id == user.id
            or user.is_admin
            or member is not None
        )
        if not can_access:
            raise AppError(404, "case_not_found", "Case was not found")
        if not await PermissionService(self.db).allows(
            user.id, "case.invite", is_admin=user.is_admin
        ):
            raise AppError(403, "invitation_not_allowed", "Your account cannot invite collaborators")
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(days=self.settings.case_invitation_expiry_days)
        invitation = CaseInvitation(
            case_id=case.id,
            invited_by_user_id=user.id,
            token_hash=_token_hash(token),
            role=role,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.commit()
        inviter_name = user.profile.display_name
        invite_url = f"{self.settings.frontend_url.rstrip('/')}/invite/{token}"
        message = (
            f"{inviter_name} invited you to collaborate on “{case.title}” in {self.settings.app_name}. "
            f"Open the invitation: {invite_url}"
        )
        return InvitationCreated(
            id=invitation.id,
            case_id=case.id,
            case_title=case.title,
            inviter_name=inviter_name,
            role=role,
            invite_url=invite_url,
            message=message,
            expires_at=expires_at,
        )

    async def preview(self, token: str) -> InvitationPreview:
        invitation = await self._lookup(token)
        case = await self.db.scalar(select(Case).where(Case.id == invitation.case_id))
        inviter = await self.db.scalar(
            select(User)
            .where(User.id == invitation.invited_by_user_id)
            .options(selectinload(User.profile))
        )
        if case is None or inviter is None:
            raise AppError(404, "invitation_not_found", "Invitation was not found")
        return InvitationPreview(
            case_id=case.id,
            case_title=case.title,
            inviter_name=inviter.profile.display_name,
            role=invitation.role,
            expires_at=invitation.expires_at,
            is_available=self._available(invitation),
        )

    async def accept(self, token: str, user: User) -> InvitationAccepted:
        invitation = await self._lookup(token, lock=True)
        if not self._available(invitation):
            raise AppError(410, "invitation_unavailable", "This invitation is expired or already used")
        case = await self.db.scalar(select(Case).where(Case.id == invitation.case_id))
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        if case.created_by_user_id == user.id:
            raise AppError(409, "owner_already_has_access", "You already own this case")
        member = await self.db.scalar(
            select(CaseMember.id).where(
                CaseMember.case_id == case.id,
                CaseMember.user_id == user.id,
            )
        )
        if member is None:
            self.db.add(
                CaseMember(
                    case_id=case.id,
                    user_id=user.id,
                    role=invitation.role,
                    invited_by_user_id=invitation.invited_by_user_id,
                )
            )
        following = await self.db.scalar(
            select(CaseFollower.id).where(
                CaseFollower.case_id == case.id,
                CaseFollower.user_id == user.id,
            )
        )
        if following is None:
            self.db.add(CaseFollower(case_id=case.id, user_id=user.id))
        invitation.accepted_by_user_id = user.id
        invitation.accepted_at = utc_now()
        await self.db.commit()
        return InvitationAccepted(
            case_id=case.id,
            message="Invitation accepted. The case is now on your My Desk.",
        )

    async def _lookup(self, token: str, *, lock: bool = False) -> CaseInvitation:
        if len(token) < 32 or len(token) > 200:
            raise AppError(404, "invitation_not_found", "Invitation was not found")
        statement = select(CaseInvitation).where(CaseInvitation.token_hash == _token_hash(token))
        if lock:
            statement = statement.with_for_update()
        invitation = await self.db.scalar(statement)
        if invitation is None:
            raise AppError(404, "invitation_not_found", "Invitation was not found")
        return invitation

    @staticmethod
    def _available(invitation: CaseInvitation) -> bool:
        now = utc_now()
        if invitation.expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        return (
            invitation.accepted_at is None
            and invitation.revoked_at is None
            and invitation.expires_at > now
        )
