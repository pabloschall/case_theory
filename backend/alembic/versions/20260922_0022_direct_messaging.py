"""direct messaging with evidence attachments

Revision ID: 20260922_0022
Revises: 20260922_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0022"
down_revision: str | None = "20260922_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "direct_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_one_id", sa.Uuid(), nullable=False),
        sa.Column("user_two_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_one_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_two_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_one_id", "user_two_id"),
    )
    op.create_index("ix_direct_conversations_user_one_id", "direct_conversations", ["user_one_id"])
    op.create_index("ix_direct_conversations_user_two_id", "direct_conversations", ["user_two_id"])
    op.create_table(
        "direct_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["direct_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_direct_messages_conversation_id", "direct_messages", ["conversation_id"])
    op.create_index("ix_direct_messages_sender_user_id", "direct_messages", ["sender_user_id"])
    op.create_index("ix_direct_messages_created_at", "direct_messages", ["created_at"])
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
    op.create_index("ix_direct_message_evidence_message_id", "direct_message_evidence", ["message_id"])
    op.create_index("ix_direct_message_evidence_evidence_id", "direct_message_evidence", ["evidence_id"])


def downgrade() -> None:
    op.drop_table("direct_message_evidence")
    op.drop_table("direct_messages")
    op.drop_table("direct_conversations")
