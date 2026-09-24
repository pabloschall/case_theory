"""case invitations and collaborators

Revision ID: 20260922_0021
Revises: 20260921_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0021"
down_revision: str | None = "20260921_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "user_id"),
    )
    op.create_index("ix_case_members_case_id", "case_members", ["case_id"])
    op.create_index("ix_case_members_user_id", "case_members", ["user_id"])
    op.create_index("ix_case_members_invited_by_user_id", "case_members", ["invited_by_user_id"])
    op.create_table(
        "case_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_invitations_case_id", "case_invitations", ["case_id"])
    op.create_index("ix_case_invitations_invited_by_user_id", "case_invitations", ["invited_by_user_id"])
    op.create_index("ix_case_invitations_token_hash", "case_invitations", ["token_hash"], unique=True)
    op.create_index("ix_case_invitations_expires_at", "case_invitations", ["expires_at"])
    op.create_index("ix_case_invitations_accepted_by_user_id", "case_invitations", ["accepted_by_user_id"])


def downgrade() -> None:
    op.drop_table("case_invitations")
    op.drop_table("case_members")
