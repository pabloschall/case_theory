import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.auth.models import RefreshSession
from app.common.errors import AppError
from app.common.timestamps import utc_now
from app.discussions.models import DiscussionComment
from app.evidence.models import Evidence, EvidenceComment
from app.moderation.models import ModerationAction, Report
from app.moderation.schemas import ModerationDecisionRequest, ReportCreate, ReportRead
from app.users.models import User, UserProfile


class ModerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_report(self, reporter: User, data: ReportCreate) -> ReportRead:
        target_user_id, summary = await self._target(data.resource_type, data.resource_id)
        if data.resource_type == "user" and target_user_id == reporter.id:
            raise AppError(422, "self_report_not_allowed", "You cannot report your own account")
        duplicate = await self.db.scalar(
            select(Report.id).where(
                Report.reporter_user_id == reporter.id,
                Report.resource_type == data.resource_type,
                Report.resource_id == data.resource_id,
                Report.status == "pending",
            )
        )
        if duplicate is not None:
            raise AppError(409, "report_already_pending", "You already reported this item")
        report = Report(
            reporter_user_id=reporter.id,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
            target_user_id=target_user_id,
            target_summary=summary[:2000],
            reason_code=data.reason_code,
            details=data.details,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return self._read(report, reporter.email)

    async def reports(
        self, status: str | None, *, page: int, page_size: int
    ) -> tuple[list[ReportRead], int]:
        reporter = aliased(User)
        statement = select(Report, reporter.email).join(
            reporter, reporter.id == Report.reporter_user_id
        )
        count_statement = select(func.count(Report.id))
        if status:
            statement = statement.where(Report.status == status)
            count_statement = count_statement.where(Report.status == status)
        rows = (
            await self.db.execute(
                statement.order_by(Report.created_at.desc(), Report.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return [self._read(report, email) for report, email in rows], int(
            await self.db.scalar(count_statement) or 0
        )

    async def decide(
        self,
        report_id: uuid.UUID,
        data: ModerationDecisionRequest,
        actor: User,
    ) -> ReportRead:
        report = await self.db.get(Report, report_id)
        if report is None:
            raise AppError(404, "report_not_found", "Report was not found")
        if data.action in {"hide", "restore"}:
            await self._set_content_visibility(report, hidden=data.action == "hide")
        elif data.action in {"lock_user", "unlock_user"}:
            await self._set_user_lock(report, actor, locked=data.action == "lock_user")
        elif data.action == "resolve":
            report.status = "resolved"
            report.reviewed_by_user_id = actor.id
            report.reviewed_at = utc_now()
            report.resolution_note = data.note
        elif data.action == "dismiss":
            report.status = "dismissed"
            report.reviewed_by_user_id = actor.id
            report.reviewed_at = utc_now()
            report.resolution_note = data.note
        self.db.add(
            ModerationAction(
                report_id=report.id,
                actor_user_id=actor.id,
                action=data.action,
                resource_type=report.resource_type,
                resource_id=report.resource_id,
                note=data.note,
            )
        )
        await self.db.commit()
        reporter_email = await self.db.scalar(
            select(User.email).where(User.id == report.reporter_user_id)
        )
        return self._read(report, reporter_email or "Deleted user")

    async def _target(self, resource_type: str, resource_id: uuid.UUID) -> tuple[uuid.UUID | None, str]:
        if resource_type == "discussion_comment":
            discussion_comment = await self.db.get(DiscussionComment, resource_id)
            if discussion_comment:
                return discussion_comment.created_by_user_id, discussion_comment.body
        elif resource_type == "evidence_comment":
            evidence_comment = await self.db.get(EvidenceComment, resource_id)
            if evidence_comment:
                return evidence_comment.author_user_id, evidence_comment.body
        elif resource_type == "evidence":
            evidence = await self.db.get(Evidence, resource_id)
            if evidence:
                return evidence.uploaded_by_user_id, (
                    f"{evidence.title}\n{evidence.description or ''}".strip()
                )
        elif resource_type == "user":
            user = await self.db.scalar(
                select(User).where(User.id == resource_id)
            )
            if user:
                profile = await self.db.get(UserProfile, user.id)
                return user.id, f"{profile.display_name if profile else user.username} (@{user.username})"
        raise AppError(404, "report_target_not_found", "The item you are reporting was not found")

    async def _set_content_visibility(self, report: Report, *, hidden: bool) -> None:
        item: DiscussionComment | EvidenceComment | Evidence | None
        if report.resource_type == "discussion_comment":
            item = await self.db.get(DiscussionComment, report.resource_id)
        elif report.resource_type == "evidence_comment":
            item = await self.db.get(EvidenceComment, report.resource_id)
        elif report.resource_type == "evidence":
            item = await self.db.get(Evidence, report.resource_id)
        else:
            raise AppError(
                422, "invalid_moderation_action", "This report does not target content"
            )
        if item is None:
            raise AppError(404, "report_target_not_found", "Reported content was not found")
        item.moderation_status = "hidden_pending_review" if hidden else "visible"

    async def _set_user_lock(self, report: Report, actor: User, *, locked: bool) -> None:
        if report.target_user_id is None:
            raise AppError(422, "invalid_moderation_action", "This report has no associated user")
        if report.target_user_id == actor.id:
            raise AppError(409, "self_lock_not_allowed", "You cannot lock your own account")
        user = await self.db.get(User, report.target_user_id)
        if user is None:
            raise AppError(404, "user_not_found", "Reported user was not found")
        if locked and user.is_admin:
            raise AppError(409, "admin_lock_not_allowed", "Another administrator must first remove admin access")
        if not locked and user.deletion_requested_at is not None:
            raise AppError(409, "deleted_user_cannot_be_unlocked", "A deleted account cannot be unlocked")
        if not locked and user.moderation_status != "locked_pending_review":
            raise AppError(409, "user_not_moderation_locked", "This account is not locked for moderation")
        user.is_active = not locked
        user.moderation_status = "locked_pending_review" if locked else "active"
        if locked:
            sessions = await self.db.scalars(
                select(RefreshSession).where(
                    RefreshSession.user_id == user.id,
                    RefreshSession.revoked_at.is_(None),
                )
            )
            now = utc_now()
            for session in sessions:
                session.revoked_at = now

    @staticmethod
    def _read(report: Report, reporter_email: str) -> ReportRead:
        return ReportRead(
            id=report.id,
            reporter_user_id=report.reporter_user_id,
            reporter_email=reporter_email,
            resource_type=report.resource_type,
            resource_id=report.resource_id,
            target_user_id=report.target_user_id,
            target_summary=report.target_summary,
            reason_code=report.reason_code,
            details=report.details,
            status=report.status,
            resolution_note=report.resolution_note,
            created_at=report.created_at,
            reviewed_at=report.reviewed_at,
        )
