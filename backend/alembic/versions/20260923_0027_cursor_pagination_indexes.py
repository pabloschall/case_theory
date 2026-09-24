"""indexes for cursor-paginated case and messaging lists

Revision ID: 20260923_0027
Revises: 20260922_0026
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260923_0027"
down_revision: str | None = "20260922_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_evidence_case_created_id",
        "evidence",
        ["case_id", "created_at", "id"],
    )
    op.create_index(
        "ix_discussion_threads_case_updated_id",
        "discussion_threads",
        ["case_id", "updated_at", "id"],
    )
    op.create_index(
        "ix_direct_messages_conversation_created_id",
        "direct_messages",
        ["conversation_id", "created_at", "id"],
    )
    op.create_index(
        "ix_direct_conversations_user_one_updated_id",
        "direct_conversations",
        ["user_one_id", "updated_at", "id"],
    )
    op.create_index(
        "ix_direct_conversations_user_two_updated_id",
        "direct_conversations",
        ["user_two_id", "updated_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_direct_conversations_user_two_updated_id",
        table_name="direct_conversations",
    )
    op.drop_index(
        "ix_direct_conversations_user_one_updated_id",
        table_name="direct_conversations",
    )
    op.drop_index(
        "ix_direct_messages_conversation_created_id",
        table_name="direct_messages",
    )
    op.drop_index(
        "ix_discussion_threads_case_updated_id",
        table_name="discussion_threads",
    )
    op.drop_index("ix_evidence_case_created_id", table_name="evidence")
