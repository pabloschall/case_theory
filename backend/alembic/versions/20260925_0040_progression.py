"""Add research progression ranks, XP ledger, and badges.

Revision ID: 20260925_0040
Revises: 20260925_0039
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925_0040"
down_revision: str | None = "20260925_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progression_ranks",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("icon_key", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_progression_ranks")),
        sa.UniqueConstraint("name", name=op.f("uq_progression_ranks_name")),
        sa.UniqueConstraint("rank_order", name=op.f("uq_progression_ranks_rank_order")),
        sa.UniqueConstraint("threshold", name=op.f("uq_progression_ranks_threshold")),
    )
    op.create_table(
        "progression_rules",
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("reason", sa.String(length=160), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("daily_cap", sa.Integer(), nullable=True),
        sa.Column("lifetime_once", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_progression_rules")),
    )
    op.create_table(
        "badge_definitions",
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("icon_key", sa.String(length=40), nullable=False),
        sa.Column("criteria_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_badge_definitions")),
        sa.UniqueConstraint("name", name=op.f("uq_badge_definitions_name")),
    )
    op.create_table(
        "progression_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lifetime_xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("highest_rank_code", sa.String(length=40), server_default="observer", nullable=False),
        sa.Column("show_rank", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("show_badges", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["highest_rank_code"],
            ["progression_ranks.code"],
            name=op.f("fk_progression_profiles_highest_rank_code_progression_ranks"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_progression_profiles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_progression_profiles")),
    )
    op.create_table(
        "progression_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=180), nullable=False),
        sa.Column("rule_code", sa.String(length=60), nullable=False),
        sa.Column("xp_delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column("is_shadow", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("displayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_progression_ledger_case_id_cases"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["rule_code"], ["progression_rules.code"], name=op.f("fk_progression_ledger_rule_code_progression_rules")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_progression_ledger_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_progression_ledger")),
        sa.UniqueConstraint("event_key", name=op.f("uq_progression_ledger_event_key")),
    )
    op.create_index(op.f("ix_progression_ledger_case_id"), "progression_ledger", ["case_id"])
    op.create_index(op.f("ix_progression_ledger_rule_code"), "progression_ledger", ["rule_code"])
    op.create_index(op.f("ix_progression_ledger_user_id"), "progression_ledger", ["user_id"])
    op.create_index("ix_progression_ledger_user_created", "progression_ledger", ["user_id", "created_at", "id"])
    op.create_table(
        "user_badges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("badge_code", sa.String(length=60), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["badge_code"],
            ["badge_definitions.code"],
            name=op.f("fk_user_badges_badge_code_badge_definitions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_badges_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_badges")),
        sa.UniqueConstraint("user_id", "badge_code", name=op.f("uq_user_badges_user_id")),
    )
    op.create_index(op.f("ix_user_badges_badge_code"), "user_badges", ["badge_code"])
    op.create_index(op.f("ix_user_badges_user_id"), "user_badges", ["user_id"])

    ranks = sa.table(
        "progression_ranks",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("threshold", sa.Integer),
        sa.column("rank_order", sa.Integer),
        sa.column("icon_key", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        ranks,
        [
            {
                "code": "observer",
                "name": "Observer",
                "threshold": 0,
                "rank_order": 1,
                "icon_key": "eye",
                "is_active": True,
            },
            {
                "code": "source_scout",
                "name": "Source Scout",
                "threshold": 100,
                "rank_order": 2,
                "icon_key": "compass",
                "is_active": True,
            },
            {
                "code": "timeline_analyst",
                "name": "Timeline Analyst",
                "threshold": 300,
                "rank_order": 3,
                "icon_key": "clock",
                "is_active": True,
            },
            {
                "code": "evidence_curator",
                "name": "Evidence Curator",
                "threshold": 700,
                "rank_order": 4,
                "icon_key": "archive",
                "is_active": True,
            },
            {
                "code": "case_researcher",
                "name": "Case Researcher",
                "threshold": 1400,
                "rank_order": 5,
                "icon_key": "search",
                "is_active": True,
            },
            {
                "code": "senior_researcher",
                "name": "Senior Researcher",
                "threshold": 2500,
                "rank_order": 6,
                "icon_key": "landmark",
                "is_active": True,
            },
            {
                "code": "archivist",
                "name": "Archivist",
                "threshold": 4500,
                "rank_order": 7,
                "icon_key": "key",
                "is_active": True,
            },
        ],
    )
    rules = sa.table(
        "progression_rules",
        sa.column("code", sa.String),
        sa.column("reason", sa.String),
        sa.column("xp", sa.Integer),
        sa.column("daily_cap", sa.Integer),
        sa.column("lifetime_once", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        rules,
        [
            {
                "code": "email_verified",
                "reason": "Email verified",
                "xp": 20,
                "daily_cap": None,
                "lifetime_once": True,
                "is_active": True,
            },
            {
                "code": "profile_completed",
                "reason": "Profile completed",
                "xp": 10,
                "daily_cap": None,
                "lifetime_once": True,
                "is_active": True,
            },
            {
                "code": "external_evidence_added",
                "reason": "Public evidence source added",
                "xp": 10,
                "daily_cap": 30,
                "lifetime_once": False,
                "is_active": True,
            },
            {
                "code": "evidence_upload_completed",
                "reason": "Evidence upload completed",
                "xp": 12,
                "daily_cap": 36,
                "lifetime_once": False,
                "is_active": True,
            },
            {
                "code": "sourced_timeline_added",
                "reason": "Sourced timeline event added",
                "xp": 8,
                "daily_cap": 32,
                "lifetime_once": False,
                "is_active": True,
            },
        ],
    )
    badges = sa.table(
        "badge_definitions",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("criteria", sa.Text),
        sa.column("category", sa.String),
        sa.column("icon_key", sa.String),
        sa.column("criteria_version", sa.Integer),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        badges,
        [
            {
                "code": "first_citation",
                "name": "First Citation",
                "description": "You added your first qualifying public source.",
                "criteria": "Add a public evidence link with a title and description.",
                "category": "research_craft",
                "icon_key": "bookmark",
                "criteria_version": 1,
                "sort_order": 1,
                "is_active": True,
            },
            {
                "code": "timeline_builder",
                "name": "Timeline Builder",
                "description": "You organized ten sourced events into case timelines.",
                "criteria": "Add 10 timeline events linked to evidence.",
                "category": "research_craft",
                "icon_key": "clock",
                "criteria_version": 1,
                "sort_order": 2,
                "is_active": True,
            },
            {
                "code": "evidence_curator",
                "name": "Evidence Curator",
                "description": "You built a well-described public evidence library.",
                "criteria": "Add 25 qualifying public evidence links.",
                "category": "research_craft",
                "icon_key": "archive",
                "criteria_version": 1,
                "sort_order": 3,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_badges_user_id"), table_name="user_badges")
    op.drop_index(op.f("ix_user_badges_badge_code"), table_name="user_badges")
    op.drop_table("user_badges")
    op.drop_index("ix_progression_ledger_user_created", table_name="progression_ledger")
    op.drop_index(op.f("ix_progression_ledger_user_id"), table_name="progression_ledger")
    op.drop_index(op.f("ix_progression_ledger_rule_code"), table_name="progression_ledger")
    op.drop_index(op.f("ix_progression_ledger_case_id"), table_name="progression_ledger")
    op.drop_table("progression_ledger")
    op.drop_table("progression_profiles")
    op.drop_table("badge_definitions")
    op.drop_table("progression_rules")
    op.drop_table("progression_ranks")
