import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.timestamps import utc_now
from app.config.settings import Settings, get_settings
from app.progression.models import (
    BadgeDefinition,
    ProgressionLedgerEntry,
    ProgressionProfile,
    ProgressionRank,
    ProgressionRule,
    UserBadge,
)
from app.progression.schemas import (
    BadgeRead,
    LedgerEntryRead,
    LedgerPage,
    ProgressionSummary,
    RankRead,
    XpReceiptRead,
)
from app.users.models import User

log = structlog.get_logger()


@dataclass(frozen=True)
class ProgressionEvent:
    user_id: uuid.UUID
    event_key: str
    rule_code: str
    resource_type: str | None = None
    resource_id: str | None = None
    case_id: uuid.UUID | None = None


class ProgressionService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def award_safely(self, event: ProgressionEvent) -> None:
        """Award after the primary action commits, without breaking that action."""
        try:
            await self.award(event)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            log.exception(
                "progression_award_failed",
                event_key=event.event_key,
                rule_code=event.rule_code,
            )

    async def award(self, event: ProgressionEvent) -> ProgressionLedgerEntry | None:
        # Serialize a member's awards so simultaneous requests cannot exceed a
        # daily cap or grant a lifetime rule twice.
        user_exists = await self.db.scalar(
            select(User.id).where(User.id == event.user_id).with_for_update()
        )
        if user_exists is None:
            return None
        existing = await self.db.scalar(
            select(ProgressionLedgerEntry).where(ProgressionLedgerEntry.event_key == event.event_key)
        )
        if existing is not None:
            return existing
        rule = await self.db.get(ProgressionRule, event.rule_code)
        if rule is None or not rule.is_active:
            return None
        if rule.lifetime_once:
            already_awarded = await self.db.scalar(
                select(ProgressionLedgerEntry.id).where(
                    ProgressionLedgerEntry.user_id == event.user_id,
                    ProgressionLedgerEntry.rule_code == rule.code,
                )
            )
            if already_awarded is not None:
                return None

        xp = rule.xp
        if rule.daily_cap is not None:
            now = utc_now()
            start = datetime(now.year, now.month, now.day, tzinfo=UTC)
            awarded_today = int(
                await self.db.scalar(
                    select(func.coalesce(func.sum(ProgressionLedgerEntry.xp_delta), 0)).where(
                        ProgressionLedgerEntry.user_id == event.user_id,
                        ProgressionLedgerEntry.rule_code == rule.code,
                        ProgressionLedgerEntry.created_at >= start,
                    )
                )
                or 0
            )
            xp = max(0, min(xp, rule.daily_cap - awarded_today))

        entry = ProgressionLedgerEntry(
            user_id=event.user_id,
            event_key=event.event_key,
            rule_code=rule.code,
            xp_delta=xp,
            reason=rule.reason,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            case_id=event.case_id,
            is_shadow=self.settings.progression_shadow_mode,
        )
        try:
            async with self.db.begin_nested():
                self.db.add(entry)
                await self.db.flush()
        except IntegrityError:
            existing_entry: ProgressionLedgerEntry | None = await self.db.scalar(
                select(ProgressionLedgerEntry).where(ProgressionLedgerEntry.event_key == event.event_key)
            )
            return existing_entry
        if self.settings.progression_shadow_mode:
            return entry

        if xp > 0:
            profile = await self.db.scalar(
                select(ProgressionProfile)
                .where(ProgressionProfile.user_id == event.user_id)
                .with_for_update()
            )
            if profile is None:
                profile = ProgressionProfile(user_id=event.user_id)
                self.db.add(profile)
                await self.db.flush()
            profile.lifetime_xp += xp
            rank = await self.db.scalar(
                select(ProgressionRank)
                .where(
                    ProgressionRank.threshold <= profile.lifetime_xp,
                    ProgressionRank.is_active.is_(True),
                )
                .order_by(ProgressionRank.rank_order.desc())
            )
            if rank is not None:
                current = await self.db.get(ProgressionRank, profile.highest_rank_code)
                if current is None or rank.rank_order > current.rank_order:
                    profile.highest_rank_code = rank.code
        await self._evaluate_badges(event)
        return entry

    async def _evaluate_badges(self, event: ProgressionEvent) -> None:
        badge_codes: list[str] = []
        if event.rule_code == "case_created":
            badge_codes.append("case_file_opened")
        if event.rule_code == "external_evidence_added":
            badge_codes.append("first_citation")
            count = await self._badge_event_count(event.user_id, "external_evidence_added")
            case_count = await self._badge_case_count(event.user_id, "external_evidence_added")
            if count >= 10 and case_count >= 3:
                badge_codes.append("source_scout")
            if count >= 25:
                badge_codes.append("evidence_curator")
        if event.rule_code == "evidence_person_linked":
            badge_codes.append("first_connection")
        if event.rule_code == "sourced_timeline_added":
            count = await self._badge_event_count(event.user_id, "sourced_timeline_added")
            if count >= 10:
                badge_codes.append("timeline_builder")
        for code in badge_codes:
            if await self.db.get(BadgeDefinition, code) is None:
                continue
            exists = await self.db.scalar(
                select(UserBadge.id).where(
                    UserBadge.user_id == event.user_id,
                    UserBadge.badge_code == code,
                )
            )
            if exists is None:
                self.db.add(UserBadge(user_id=event.user_id, badge_code=code))

    async def _badge_event_count(self, user_id: uuid.UUID, rule_code: str) -> int:
        return int(
            await self.db.scalar(
                select(func.count(ProgressionLedgerEntry.id)).where(
                    ProgressionLedgerEntry.user_id == user_id,
                    ProgressionLedgerEntry.rule_code == rule_code,
                    ProgressionLedgerEntry.is_shadow.is_(False),
                )
            )
            or 0
        )

    async def _badge_case_count(self, user_id: uuid.UUID, rule_code: str) -> int:
        return int(
            await self.db.scalar(
                select(func.count(func.distinct(ProgressionLedgerEntry.case_id))).where(
                    ProgressionLedgerEntry.user_id == user_id,
                    ProgressionLedgerEntry.rule_code == rule_code,
                    ProgressionLedgerEntry.case_id.is_not(None),
                    ProgressionLedgerEntry.is_shadow.is_(False),
                )
            )
            or 0
        )

    async def summary(self, user_id: uuid.UUID) -> ProgressionSummary:
        profile = await self.db.get(ProgressionProfile, user_id)
        lifetime_xp = profile.lifetime_xp if profile else 0
        ranks = list(
            (
                await self.db.scalars(
                    select(ProgressionRank)
                    .where(ProgressionRank.is_active.is_(True))
                    .order_by(ProgressionRank.rank_order)
                )
            ).all()
        )
        if not ranks:
            raise RuntimeError("Progression ranks are not initialized")
        current_index = max(index for index, rank in enumerate(ranks) if rank.threshold <= lifetime_xp)
        current = ranks[current_index]
        next_rank = ranks[current_index + 1] if current_index + 1 < len(ranks) else None
        if next_rank:
            span = next_rank.threshold - current.threshold
            progress = int(((lifetime_xp - current.threshold) / span) * 100)
            xp_to_next = next_rank.threshold - lifetime_xp
        else:
            progress = 100
            xp_to_next = None

        earned_rows = (
            await self.db.execute(
                select(UserBadge, BadgeDefinition)
                .join(BadgeDefinition, BadgeDefinition.code == UserBadge.badge_code)
                .where(UserBadge.user_id == user_id)
            )
        ).all()
        earned = {badge.code: (user_badge, badge) for user_badge, badge in earned_rows}
        definitions = list(
            (
                await self.db.scalars(
                    select(BadgeDefinition)
                    .where(BadgeDefinition.is_active.is_(True))
                    .order_by(BadgeDefinition.sort_order)
                )
            ).all()
        )
        badges = [self._badge_read(definition, earned.get(definition.code)) for definition in definitions]
        pending_badges = [
            self._badge_read(definition, (user_badge, definition))
            for user_badge, definition in earned_rows
            if user_badge.revealed_at is None
        ]
        receipts = list(
            (
                await self.db.scalars(
                    select(ProgressionLedgerEntry)
                    .where(
                        ProgressionLedgerEntry.user_id == user_id,
                        ProgressionLedgerEntry.is_shadow.is_(False),
                        ProgressionLedgerEntry.displayed_at.is_(None),
                        ProgressionLedgerEntry.xp_delta > 0,
                    )
                    .order_by(ProgressionLedgerEntry.created_at)
                    .limit(5)
                )
            ).all()
        )
        return ProgressionSummary(
            lifetime_xp=lifetime_xp,
            show_rank=profile.show_rank if profile else True,
            show_badges=profile.show_badges if profile else True,
            rank=self._rank_read(current),
            next_rank=self._rank_read(next_rank) if next_rank else None,
            progress_percent=max(0, min(progress, 100)),
            xp_to_next_rank=xp_to_next,
            badges=badges,
            pending_badges=pending_badges,
            pending_receipts=[
                XpReceiptRead(
                    id=item.id,
                    xp=item.xp_delta,
                    reason=item.reason,
                    created_at=item.created_at,
                )
                for item in receipts
            ],
        )

    async def ledger(self, user_id: uuid.UUID, page: int, page_size: int) -> LedgerPage:
        where = (
            ProgressionLedgerEntry.user_id == user_id,
            ProgressionLedgerEntry.is_shadow.is_(False),
            ProgressionLedgerEntry.xp_delta > 0,
        )
        total = int(await self.db.scalar(select(func.count(ProgressionLedgerEntry.id)).where(*where)) or 0)
        items = list(
            (
                await self.db.scalars(
                    select(ProgressionLedgerEntry)
                    .where(*where)
                    .order_by(ProgressionLedgerEntry.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return LedgerPage(
            items=[
                LedgerEntryRead(
                    id=item.id,
                    rule_code=item.rule_code,
                    xp=item.xp_delta,
                    reason=item.reason,
                    resource_type=item.resource_type,
                    resource_id=item.resource_id,
                    created_at=item.created_at,
                )
                for item in items
            ],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def acknowledge(self, user_id: uuid.UUID, receipt_ids: list[uuid.UUID], badge_codes: list[str]) -> None:
        now = utc_now()
        if receipt_ids:
            await self.db.execute(
                update(ProgressionLedgerEntry)
                .where(
                    ProgressionLedgerEntry.user_id == user_id,
                    ProgressionLedgerEntry.id.in_(receipt_ids),
                )
                .values(displayed_at=now)
            )
        if badge_codes:
            await self.db.execute(
                update(UserBadge)
                .where(
                    UserBadge.user_id == user_id,
                    UserBadge.badge_code.in_(badge_codes),
                )
                .values(revealed_at=now)
            )
        await self.db.commit()

    async def update_privacy(self, user_id: uuid.UUID, show_rank: bool, show_badges: bool) -> None:
        profile = await self.db.get(ProgressionProfile, user_id)
        if profile is None:
            profile = ProgressionProfile(user_id=user_id)
            self.db.add(profile)
        profile.show_rank = show_rank
        profile.show_badges = show_badges
        await self.db.commit()

    @staticmethod
    def _rank_read(rank: ProgressionRank) -> RankRead:
        return RankRead(
            code=rank.code,
            name=rank.name,
            threshold=rank.threshold,
            icon_key=rank.icon_key,
        )

    @staticmethod
    def _badge_read(
        definition: BadgeDefinition,
        earned: tuple[UserBadge, BadgeDefinition] | None,
    ) -> BadgeRead:
        return BadgeRead(
            code=definition.code,
            name=definition.name,
            description=definition.description,
            criteria=definition.criteria,
            category=definition.category,
            icon_key=definition.icon_key,
            earned_at=earned[0].earned_at if earned else None,
        )
