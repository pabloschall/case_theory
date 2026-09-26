"""Add persistent ordering to shared timeline events.

Revision ID: 20260926_0043
Revises: 20260926_0042
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260926_0043"
down_revision: str | None = "20260926_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("timeline_events", sa.Column("position", sa.Integer(), nullable=True))
    op.create_index(
        "ix_timeline_events_case_position",
        "timeline_events",
        ["case_id", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_timeline_events_case_position", table_name="timeline_events")
    op.drop_column("timeline_events", "position")
