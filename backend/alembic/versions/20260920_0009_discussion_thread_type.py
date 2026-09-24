"""Classify discussion threads by research purpose."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0009"
down_revision: str | None = "20260920_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discussion_threads",
        sa.Column("thread_type", sa.String(length=24), server_default="question", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("discussion_threads", "thread_type")
