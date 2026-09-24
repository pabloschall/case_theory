"""Add sourced AI discussion prompts."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0015"
down_revision: str | None = "20260921_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discussion_threads",
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "discussion_threads",
        sa.Column("review_status", sa.String(30), server_default="published", nullable=False),
    )
    op.create_table(
        "discussion_thread_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["discussion_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "source_id"),
    )
    op.create_index(
        "ix_discussion_thread_sources_thread_id", "discussion_thread_sources", ["thread_id"]
    )
    op.create_index(
        "ix_discussion_thread_sources_source_id", "discussion_thread_sources", ["source_id"]
    )


def downgrade() -> None:
    op.drop_table("discussion_thread_sources")
    op.drop_column("discussion_threads", "review_status")
    op.drop_column("discussion_threads", "ai_generated")
