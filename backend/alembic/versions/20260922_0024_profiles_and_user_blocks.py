"""editable profiles, avatar uploads, and user blocks

Revision ID: 20260922_0024
Revises: 20260922_0023
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0024"
down_revision: str | None = "20260922_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profiles", sa.Column("avatar_object_key", sa.String(length=1024), nullable=True)
    )
    op.create_unique_constraint(
        "uq_user_profiles_avatar_object_key", "user_profiles", ["avatar_object_key"]
    )
    op.create_table(
        "user_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocker_user_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["blocked_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_user_id", "blocked_user_id"),
    )
    op.create_index("ix_user_blocks_blocker_user_id", "user_blocks", ["blocker_user_id"])
    op.create_index("ix_user_blocks_blocked_user_id", "user_blocks", ["blocked_user_id"])
    op.create_table(
        "user_avatar_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_object_key"),
    )
    op.create_index("ix_user_avatar_uploads_user_id", "user_avatar_uploads", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_avatar_uploads")
    op.drop_table("user_blocks")
    op.drop_constraint("uq_user_profiles_avatar_object_key", "user_profiles", type_="unique")
    op.drop_column("user_profiles", "avatar_object_key")
