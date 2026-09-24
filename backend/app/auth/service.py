import uuid
from datetime import timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.legal import POLICY_VERSIONS, policy_checksum
from app.auth.models import AccountActionToken, LegalAcceptance, RefreshSession
from app.auth.schemas import RegisterRequest
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    new_account_token,
    token_hash,
    verify_password,
)
from app.auth.tasks import queue_password_reset_email, queue_verification_email
from app.common.errors import AppError
from app.common.ids import new_uuid
from app.common.timestamps import utc_now
from app.config.settings import Settings
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def register(
        self,
        data: RegisterRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
        request_id: str | None,
    ) -> User:
        plan = await self.db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "free", SubscriptionPlan.is_active.is_(True))
        )
        if plan is None:
            raise AppError(503, "plans_not_initialized", "Subscription plans are not initialized")
        user = User(
            email=data.email.lower(),
            username=data.username.lower(),
            password_hash=hash_password(data.password),
            profile=UserProfile(display_name=data.display_name.strip()),
        )
        try:
            self.db.add(user)
            await self.db.flush()
            self.db.add(UserSubscription(user_id=user.id, plan_id=plan.id))
            for policy_type, version in POLICY_VERSIONS.items():
                self.db.add(
                    LegalAcceptance(
                        user_id=user.id,
                        policy_type=policy_type,
                        policy_version=version,
                        document_checksum=policy_checksum(policy_type),
                        user_agent=user_agent[:500] if user_agent else None,
                        ip_address=ip_address,
                        request_id=request_id,
                    )
                )
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            conflict = str(exc.orig).lower()
            if "users_username" in conflict or "users.username" in conflict:
                raise AppError(409, "username_taken", "That username is already taken") from exc
            if "users_email" in conflict or "users.email" in conflict:
                raise AppError(409, "email_registered", "An account with that email already exists") from exc
            raise AppError(409, "account_exists", "An account with that email or username already exists") from exc
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.db.scalar(select(User).where(User.email == email.lower()))
        if user is None or not verify_password(user.password_hash, password):
            raise AppError(401, "invalid_credentials", "Email or password is incorrect")
        if not user.is_active:
            raise AppError(403, "account_inactive", "This account is not active")
        return user

    async def request_email_verification(self, email: str) -> None:
        user = await self.db.scalar(
            select(User).where(User.email == email.lower(), User.is_active.is_(True))
        )
        if user is None or user.is_verified:
            return
        token = await self._issue_account_token(
            user,
            "email_verification",
            timedelta(hours=self.settings.email_verification_expiry_hours),
        )
        queue_verification_email(user.email, token)

    async def confirm_email(self, raw_token: str) -> User:
        token = await self.db.scalar(
            select(AccountActionToken)
            .where(
                AccountActionToken.purpose == "email_verification",
                AccountActionToken.token_hash == token_hash(raw_token),
                AccountActionToken.expires_at > utc_now(),
            )
            .with_for_update()
        )
        if token is None:
            raise AppError(400, "invalid_verification_token", "Verification link is invalid or expired")
        user = await self.db.scalar(select(User).where(User.id == token.user_id))
        if user is None or not user.is_active:
            raise AppError(400, "invalid_verification_token", "Verification link is invalid or expired")
        if token.used_at is None:
            token.used_at = utc_now()
            user.is_verified = True
            await self.db.commit()
        elif not user.is_verified:
            raise AppError(400, "invalid_verification_token", "Verification link is invalid or expired")
        return user

    async def request_password_reset(self, email: str) -> None:
        user = await self.db.scalar(
            select(User).where(User.email == email.lower(), User.is_active.is_(True))
        )
        if user is None:
            return
        token = await self._issue_account_token(
            user,
            "password_reset",
            timedelta(minutes=self.settings.password_reset_expiry_minutes),
        )
        queue_password_reset_email(user.email, token)

    async def reset_password(self, raw_token: str, password: str) -> None:
        token = await self.db.scalar(
            select(AccountActionToken)
            .where(
                AccountActionToken.purpose == "password_reset",
                AccountActionToken.token_hash == token_hash(raw_token),
                AccountActionToken.used_at.is_(None),
                AccountActionToken.expires_at > utc_now(),
            )
            .with_for_update()
        )
        if token is None:
            raise AppError(400, "invalid_password_reset_token", "Password reset link is invalid or expired")
        user = await self.db.scalar(select(User).where(User.id == token.user_id, User.is_active.is_(True)))
        if user is None:
            raise AppError(400, "invalid_password_reset_token", "Password reset link is invalid or expired")
        now = utc_now()
        user.password_hash = hash_password(password)
        token.used_at = now
        await self.db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.db.commit()

    async def _issue_account_token(self, user: User, purpose: str, lifetime: timedelta) -> str:
        now = utc_now()
        await self.db.execute(
            update(AccountActionToken)
            .where(
                AccountActionToken.user_id == user.id,
                AccountActionToken.purpose == purpose,
                AccountActionToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        raw_token = new_account_token()
        self.db.add(
            AccountActionToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=token_hash(raw_token),
                expires_at=now + lifetime,
            )
        )
        await self.db.commit()
        return raw_token

    async def create_session(self, user: User, user_agent: str | None, ip_address: str | None) -> tuple[str, str]:
        session_id = new_uuid()
        refresh_token, expires_at = create_refresh_token(user.id, session_id, self.settings)
        self.db.add(
            RefreshSession(
                id=session_id,
                user_id=user.id,
                token_hash=token_hash(refresh_token),
                user_agent=user_agent[:500] if user_agent else None,
                ip_address=ip_address,
                expires_at=expires_at,
            )
        )
        await self.db.commit()
        return create_access_token(user.id, self.settings), refresh_token

    async def rotate_session(self, refresh_token: str) -> tuple[str, str]:
        from app.auth.security import decode_token

        try:
            payload = decode_token(refresh_token, "refresh", self.settings)
            session_id = uuid.UUID(payload["sid"])
            user_id = uuid.UUID(payload["sub"])
        except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
            raise AppError(401, "invalid_session", "Session is invalid or expired") from exc
        session = await self.db.scalar(
            select(RefreshSession)
            .where(
                RefreshSession.id == session_id,
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.rotated_at.is_(None),
                RefreshSession.expires_at > utc_now(),
            )
            .with_for_update()
        )
        if session is None or session.token_hash != token_hash(refresh_token):
            raise AppError(401, "invalid_session", "Session is invalid or expired")
        user = await self.db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
        if user is None:
            raise AppError(401, "invalid_session", "Session is invalid or expired")
        session.rotated_at = utc_now()
        return await self.create_session(user, session.user_agent, session.ip_address)

    async def revoke_session(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        session = await self.db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash(refresh_token))
        )
        if session is not None and session.revoked_at is None:
            session.revoked_at = utc_now()
            await self.db.commit()
