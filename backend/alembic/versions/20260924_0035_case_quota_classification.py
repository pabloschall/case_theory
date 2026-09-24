"""classify cases that consume the weekly allowance

Revision ID: 20260924_0035
Revises: 20260924_0034
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260924_0035"
down_revision: str | None = "20260924_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column(
            "counts_toward_weekly_limit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE cases
            SET counts_toward_weekly_limit = false
            WHERE privacy = 'public'
              AND NOT EXISTS (
                  SELECT 1 FROM case_generation_jobs
                  WHERE case_generation_jobs.case_id = cases.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM case_sources
                  WHERE case_sources.case_id = cases.id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("cases", "counts_toward_weekly_limit")
