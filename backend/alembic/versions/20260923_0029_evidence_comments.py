"""add evidence comments

Revision ID: 20260923_0029
Revises: 20260923_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_0029"
down_revision: str | None = "20260923_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_comments_author_user_id",
        "evidence_comments",
        ["author_user_id"],
    )
    op.create_index(
        "ix_evidence_comments_evidence_id",
        "evidence_comments",
        ["evidence_id"],
    )
    op.create_index(
        "ix_evidence_comments_evidence_created_id",
        "evidence_comments",
        ["evidence_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_table("evidence_comments")
