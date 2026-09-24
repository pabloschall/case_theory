"""add discussion thread votes

Revision ID: 20260923_0030
Revises: 20260923_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_0030"
down_revision: str | None = "20260923_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discussion_thread_votes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["discussion_threads.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "user_id"),
    )
    op.create_index(
        "ix_discussion_thread_votes_thread_id",
        "discussion_thread_votes",
        ["thread_id"],
    )
    op.create_index(
        "ix_discussion_thread_votes_user_id",
        "discussion_thread_votes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("discussion_thread_votes")
