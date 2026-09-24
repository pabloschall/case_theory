"""numeric user tiers and persisted AI case quotas

Revision ID: 20260922_0026
Revises: 20260922_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0026"
down_revision: str | None = "20260922_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("tier_level", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("daily_ai_case_limit", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("lifetime_ai_case_limit", sa.Integer(), nullable=False, server_default="0"),
    )
    plans = sa.table(
        "subscription_plans",
        sa.column("code", sa.String()),
        sa.column("tier_level", sa.Integer()),
        sa.column("daily_ai_case_limit", sa.Integer()),
        sa.column("lifetime_ai_case_limit", sa.Integer()),
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "admin")
        .values(tier_level=0, daily_ai_case_limit=-1, lifetime_ai_case_limit=-1)
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "free")
        .values(tier_level=1, daily_ai_case_limit=0, lifetime_ai_case_limit=1)
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "investigator")
        .values(tier_level=2, daily_ai_case_limit=2, lifetime_ai_case_limit=0)
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "lead")
        .values(tier_level=3, daily_ai_case_limit=5, lifetime_ai_case_limit=0)
    )
    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column("usage_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id"),
    )
    op.create_index("ix_ai_usage_records_user_id", "ai_usage_records", ["user_id"])
    op.create_index("ix_ai_usage_records_case_id", "ai_usage_records", ["case_id"], unique=True)
    op.create_index("ix_ai_usage_records_usage_type", "ai_usage_records", ["usage_type"])
    op.create_index("ix_ai_usage_records_created_at", "ai_usage_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_usage_records")
    op.drop_column("subscription_plans", "lifetime_ai_case_limit")
    op.drop_column("subscription_plans", "daily_ai_case_limit")
    op.drop_column("subscription_plans", "tier_level")
