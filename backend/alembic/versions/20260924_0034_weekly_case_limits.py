"""add weekly case creation limits

Revision ID: 20260924_0034
Revises: 20260924_0033
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260924_0034"
down_revision: str | None = "20260924_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("weekly_case_limit", sa.Integer(), nullable=False, server_default="1"),
    )
    plans = sa.table(
        "subscription_plans",
        sa.column("code", sa.String()),
        sa.column("weekly_case_limit", sa.Integer()),
    )
    op.execute(plans.update().where(plans.c.code == "free").values(weekly_case_limit=1))
    op.execute(
        plans.update().where(plans.c.code.in_(["investigator", "lead"])).values(weekly_case_limit=5)
    )
    op.execute(plans.update().where(plans.c.code == "admin").values(weekly_case_limit=-1))


def downgrade() -> None:
    op.drop_column("subscription_plans", "weekly_case_limit")
