"""replace message evidence links with private file attachments

Revision ID: 20260922_0023
Revises: 20260922_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0023"
down_revision: str | None = "20260922_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("direct_message_evidence")
    op.create_table(
        "message_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["direct_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["direct_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_object_key"),
    )
    op.create_index(
        "ix_message_attachments_conversation_id", "message_attachments", ["conversation_id"]
    )
    op.create_index(
        "ix_message_attachments_message_id", "message_attachments", ["message_id"]
    )
    op.create_index(
        "ix_message_attachments_uploaded_by_user_id",
        "message_attachments",
        ["uploaded_by_user_id"],
    )
    op.create_index(
        "ix_message_attachments_sha256_hash", "message_attachments", ["sha256_hash"]
    )


def downgrade() -> None:
    op.drop_table("message_attachments")
    op.create_table(
        "direct_message_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["direct_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "evidence_id"),
    )
