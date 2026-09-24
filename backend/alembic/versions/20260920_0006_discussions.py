"""Add flat case discussion threads, comments, and reactions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0006"
down_revision: str | None = "20260920_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discussion_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name="fk_discussion_threads_case_id_cases", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_discussion_threads_created_by_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discussion_threads"),
    )
    op.create_index("ix_discussion_threads_case_id", "discussion_threads", ["case_id"])
    op.create_index("ix_discussion_threads_created_by_user_id", "discussion_threads", ["created_by_user_id"])
    op.create_table(
        "discussion_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["discussion_threads.id"],
            name="fk_discussion_comments_thread_id_discussion_threads",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_discussion_comments_created_by_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discussion_comments"),
    )
    op.create_index("ix_discussion_comments_thread_id", "discussion_comments", ["thread_id"])
    op.create_index("ix_discussion_comments_created_by_user_id", "discussion_comments", ["created_by_user_id"])
    op.create_table(
        "discussion_reactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["discussion_comments.id"],
            name="fk_discussion_reactions_comment_id_discussion_comments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_discussion_reactions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discussion_reactions"),
        sa.UniqueConstraint("comment_id", "user_id", "emoji", name="uq_discussion_reactions_comment_id"),
    )
    op.create_index("ix_discussion_reactions_comment_id", "discussion_reactions", ["comment_id"])
    op.create_index("ix_discussion_reactions_user_id", "discussion_reactions", ["user_id"])


def downgrade() -> None:
    op.drop_table("discussion_reactions")
    op.drop_table("discussion_comments")
    op.drop_table("discussion_threads")
