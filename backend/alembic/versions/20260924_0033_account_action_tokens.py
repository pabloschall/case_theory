"""add account action tokens

Revision ID: 20260924_0033
Revises: 20260923_0032
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260924_0033"
down_revision: str | None = "20260923_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_account_action_tokens_user_id", "account_action_tokens", ["user_id"])
    op.create_index("ix_account_action_tokens_purpose", "account_action_tokens", ["purpose"])
    op.create_index("ix_account_action_tokens_expires_at", "account_action_tokens", ["expires_at"])
    op.create_index(
        "ix_account_action_tokens_lookup", "account_action_tokens", ["purpose", "token_hash"]
    )


def downgrade() -> None:
    op.drop_table("account_action_tokens")
