"""Add case evidence and reusable discussion/timeline links."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0007"
down_revision: str | None = "20260920_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("storage_object_key", sa.String(1024), nullable=True),
        sa.Column("original_filename", sa.String(500), nullable=True),
        sa.Column("mime_type", sa.String(150), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("visibility", sa.String(30), nullable=False),
        sa.Column("processing_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_object_key"),
    )
    op.create_index("ix_evidence_case_id", "evidence", ["case_id"])
    op.create_index("ix_evidence_uploaded_by_user_id", "evidence", ["uploaded_by_user_id"])
    op.create_index("ix_evidence_sha256_hash", "evidence", ["sha256_hash"])
    op.create_table(
        "discussion_thread_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["discussion_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "evidence_id"),
    )
    op.create_index("ix_discussion_thread_evidence_thread_id", "discussion_thread_evidence", ["thread_id"])
    op.create_index(
        "ix_discussion_thread_evidence_evidence_id", "discussion_thread_evidence", ["evidence_id"]
    )
    op.create_index(
        "ix_discussion_thread_evidence_created_by_user_id",
        "discussion_thread_evidence",
        ["created_by_user_id"],
    )
    op.create_table(
        "timeline_event_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timeline_event_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["timeline_event_id"], ["timeline_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timeline_event_id", "evidence_id"),
    )
    op.create_index("ix_timeline_event_evidence_timeline_event_id", "timeline_event_evidence", ["timeline_event_id"])
    op.create_index("ix_timeline_event_evidence_evidence_id", "timeline_event_evidence", ["evidence_id"])
    op.create_index(
        "ix_timeline_event_evidence_created_by_user_id",
        "timeline_event_evidence",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_table("timeline_event_evidence")
    op.drop_table("discussion_thread_evidence")
    op.drop_table("evidence")
