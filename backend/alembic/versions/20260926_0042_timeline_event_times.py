"""Store local occurrence times for timeline events.

Revision ID: 20260926_0042
Revises: 20260925_0041
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260926_0042"
down_revision: str | None = "20260925_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("timeline_events", sa.Column("occurred_time", sa.Time(), nullable=True))
    op.create_index(
        "ix_timeline_events_case_date_time_id",
        "timeline_events",
        ["case_id", "occurred_on", "occurred_time", "id"],
    )
    op.drop_index(
        "ix_case_timeline_entries_case_date_id",
        table_name="case_timeline_entries",
    )
    op.add_column(
        "case_timeline_entries",
        sa.Column("occurred_time", sa.Time(), nullable=True),
    )
    op.create_index(
        "ix_case_timeline_entries_case_date_time_id",
        "case_timeline_entries",
        ["case_id", "occurred_on", "occurred_time", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_case_timeline_entries_case_date_time_id",
        table_name="case_timeline_entries",
    )
    op.drop_column("case_timeline_entries", "occurred_time")
    op.create_index(
        "ix_case_timeline_entries_case_date_id",
        "case_timeline_entries",
        ["case_id", "occurred_on", "id"],
    )
    op.drop_index(
        "ix_timeline_events_case_date_time_id",
        table_name="timeline_events",
    )
    op.drop_column("timeline_events", "occurred_time")
