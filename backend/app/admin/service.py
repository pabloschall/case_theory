import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.models import AuditLog
from app.admin.schemas import AdminCaseRead, AdminUserCreate, AdminUserRead
from app.auth.models import RefreshSession
from app.auth.security import hash_password
from app.cases.models import Case
from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.evidence.models import Evidence
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def users(
        self, query: str | None, *, page: int, page_size: int
    ) -> tuple[list[AdminUserRead], int]:
        filters = []
        if query and (normalized := query.strip()):
            pattern = f"%{normalized}%"
            filters.append(
                or_(
                    User.email.ilike(pattern),
                    User.username.ilike(pattern),
                    UserProfile.display_name.ilike(pattern),
                )
            )
        statement = (
            select(User)
            .join(UserProfile, UserProfile.user_id == User.id)
            .options(selectinload(User.profile))
            .where(User.deletion_requested_at.is_(None))
        )
        count_statement = (
            select(func.count(User.id))
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.deletion_requested_at.is_(None))
        )
        for condition in filters:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        result = await self.db.scalars(
            statement.order_by(User.created_at.desc(), User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        users = list(result)
        subscriptions = await self._subscriptions([user.id for user in users])
        case_counts = await self._case_counts([user.id for user in users])
        items = [
            self._user_read(user, subscriptions.get(user.id), case_counts.get(user.id, 0))
            for user in users
        ]
        return items, int(await self.db.scalar(count_statement) or 0)

    async def create_admin(self, data: AdminUserCreate, actor: User) -> AdminUserRead:
        plan = await self.db.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.tier_level == 0,
                SubscriptionPlan.is_active.is_(True),
            )
        )
        if plan is None:
            raise AppError(503, "admin_plan_unavailable", "The administrator tier is not configured")
        user = User(
            email=str(data.email).lower(),
            username=data.username.lower(),
            password_hash=hash_password(data.password),
            is_admin=True,
            profile=UserProfile(display_name=data.display_name.strip()),
        )
        self.db.add(user)
        try:
            await self.db.flush()
            self.db.add(UserSubscription(user_id=user.id, plan_id=plan.id))
            self.db.add(
                AuditLog(
                    actor_user_id=actor.id,
                    action="user.admin_created",
                    resource_type="user",
                    resource_id=user.id,
                    before_snapshot=None,
                    after_snapshot={
                        "email": user.email,
                        "username": user.username,
                        "tier_level": 0,
                        "plan_code": plan.code,
                        "is_admin": True,
                    },
                )
            )
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AppError(
                409,
                "account_exists",
                "An account with that email or username already exists",
            ) from exc
        return self._user_read(user, plan, 0)

    async def cases(
        self, query: str | None, *, page: int, page_size: int
    ) -> tuple[list[AdminCaseRead], int]:
        filters = []
        if query and (normalized := query.strip()):
            pattern = f"%{normalized}%"
            filters.append(
                or_(
                    User.email.ilike(pattern),
                    User.username.ilike(pattern),
                    UserProfile.display_name.ilike(pattern),
                    Case.title.ilike(pattern),
                )
            )
        statement = (
            select(Case)
            .join(User, User.id == Case.created_by_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .options(selectinload(Case.owner).selectinload(User.profile))
        )
        count_statement = (
            select(func.count(Case.id))
            .join(User, User.id == Case.created_by_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
        )
        for condition in filters:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        result = await self.db.scalars(
            statement.order_by(Case.created_at.desc(), Case.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [self._case_read(case) for case in result], int(
            await self.db.scalar(count_statement) or 0
        )

    async def update_tier(
        self, target_user_id: uuid.UUID, tier_level: int, actor: User
    ) -> AdminUserRead:
        if target_user_id == actor.id:
            raise AppError(
                409,
                "self_tier_change_not_allowed",
                "Use another administrator account to change your own tier",
            )
        user = await self.db.scalar(
            select(User)
            .where(User.id == target_user_id)
            .options(selectinload(User.profile))
        )
        if user is None:
            raise AppError(404, "user_not_found", "User was not found")
        plan = await self.db.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.tier_level == tier_level,
                SubscriptionPlan.is_active.is_(True),
            )
        )
        if plan is None:
            raise AppError(422, "tier_unavailable", "That tier is not configured")
        subscriptions = list(
            await self.db.scalars(
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user.id,
                    UserSubscription.is_active.is_(True),
                )
                .options(selectinload(UserSubscription.plan))
                .order_by(UserSubscription.starts_at.desc())
            )
        )
        previous_plan = subscriptions[0].plan if subscriptions else None
        before = {
            "tier_level": previous_plan.tier_level if previous_plan else 1,
            "plan_code": previous_plan.code if previous_plan else "free",
            "is_admin": user.is_admin,
        }
        if subscriptions:
            subscriptions[0].plan_id = plan.id
            for duplicate in subscriptions[1:]:
                duplicate.is_active = False
        else:
            self.db.add(UserSubscription(user_id=user.id, plan_id=plan.id))
        user.is_admin = tier_level == 0
        after = {
            "tier_level": plan.tier_level,
            "plan_code": plan.code,
            "is_admin": user.is_admin,
        }
        self.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="user.tier_changed",
                resource_type="user",
                resource_id=user.id,
                before_snapshot=before,
                after_snapshot=after,
            )
        )
        await self.db.commit()
        return self._user_read(user, plan, await self._case_count(user.id))

    async def delete_user(self, target_user_id: uuid.UUID, actor: User) -> None:
        if target_user_id == actor.id:
            raise AppError(409, "self_deletion_not_allowed", "You cannot delete your own administrator account")
        user = await self.db.scalar(
            select(User)
            .where(User.id == target_user_id, User.deletion_requested_at.is_(None))
            .options(selectinload(User.profile))
        )
        if user is None:
            raise AppError(404, "user_not_found", "User was not found")
        subscriptions = list(
            await self.db.scalars(select(UserSubscription).where(UserSubscription.user_id == user.id))
        )
        sessions = list(await self.db.scalars(select(RefreshSession).where(RefreshSession.user_id == user.id)))
        now = utc_now()
        self.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="user.deleted",
                resource_type="user",
                resource_id=user.id,
                before_snapshot={
                    "email": user.email,
                    "username": user.username,
                    "display_name": user.profile.display_name,
                    "is_admin": user.is_admin,
                },
                after_snapshot={"deleted": True, "anonymized": True},
            )
        )
        user.email = f"deleted-{user.id}@deleted.invalid"
        user.username = f"deleted_{user.id.hex}"
        user.password_hash = hash_password(str(uuid.uuid4()))
        user.is_active = False
        user.is_verified = False
        user.is_admin = False
        user.deletion_requested_at = now
        user.profile.display_name = "Deleted user"
        user.profile.bio = None
        user.profile.avatar_url = None
        user.profile.avatar_object_key = None
        for subscription in subscriptions:
            subscription.is_active = False
            subscription.ends_at = now
        for session in sessions:
            session.revoked_at = now
        await self.db.commit()

    async def delete_case(self, case_id: uuid.UUID, actor: User) -> set[str]:
        case = await self.db.scalar(
            select(Case)
            .where(Case.id == case_id)
            .options(selectinload(Case.owner).selectinload(User.profile))
        )
        if case is None:
            raise AppError(404, "case_not_found", "Case was not found")
        stored_keys = await self.db.scalars(
            select(Evidence.storage_object_key).where(
                Evidence.case_id == case_id,
                Evidence.storage_object_key.is_not(None),
            )
        )
        object_keys = {key for key in stored_keys if key}
        if case.cover_image_object_key:
            object_keys.add(case.cover_image_object_key)
        self.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="case.deleted",
                resource_type="case",
                resource_id=case.id,
                before_snapshot={
                    "title": case.title,
                    "privacy": case.privacy,
                    "status": case.status,
                    "owner_id": str(case.created_by_user_id),
                    "owner_email": case.owner.email,
                },
                after_snapshot=None,
            )
        )
        await self.db.delete(case)
        await self.db.commit()
        return object_keys

    async def _subscriptions(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SubscriptionPlan]:
        if not user_ids:
            return {}
        result = await self.db.scalars(
            select(UserSubscription)
            .where(
                UserSubscription.user_id.in_(user_ids),
                UserSubscription.is_active.is_(True),
            )
            .options(selectinload(UserSubscription.plan))
            .order_by(UserSubscription.starts_at.desc())
        )
        subscriptions: dict[uuid.UUID, SubscriptionPlan] = {}
        for subscription in result:
            subscriptions.setdefault(subscription.user_id, subscription.plan)
        return subscriptions

    async def _case_counts(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not user_ids:
            return {}
        result = await self.db.execute(
            select(Case.created_by_user_id, func.count(Case.id))
            .where(Case.created_by_user_id.in_(user_ids))
            .group_by(Case.created_by_user_id)
        )
        return {user_id: int(count) for user_id, count in result.all()}

    async def _case_count(self, user_id: uuid.UUID) -> int:
        return int(
            await self.db.scalar(
                select(func.count(Case.id)).where(Case.created_by_user_id == user_id)
            )
            or 0
        )

    @staticmethod
    def _user_read(
        user: User, plan: SubscriptionPlan | None, case_count: int
    ) -> AdminUserRead:
        return AdminUserRead(
            id=user.id,
            email=user.email,
            username=user.username,
            display_name=user.profile.display_name,
            is_active=user.is_active,
            moderation_status=user.moderation_status,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
            tier_level=plan.tier_level if plan else 1,
            plan_code=plan.code if plan else "free",
            plan_name=plan.name if plan else "Free",
            case_count=case_count,
            created_at=user.created_at,
        )

    @staticmethod
    def _case_read(case: Case) -> AdminCaseRead:
        return AdminCaseRead(
            id=case.id,
            title=case.title,
            status=case.status,
            privacy=case.privacy,
            ai_research_status=case.ai_research_status,
            cover_image_url=case.cover_image_url,
            owner_id=case.owner.id,
            owner_email=case.owner.email,
            owner_username=case.owner.username,
            owner_display_name=case.owner.profile.display_name,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
