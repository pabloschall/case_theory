"""add moderation reports and review states

Revision ID: 20260923_0032
Revises: 20260923_0031
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_0032"
down_revision: str | None = "20260923_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("moderation_status", sa.String(30), nullable=False, server_default="active"))
    op.create_index("ix_users_moderation_status", "users", ["moderation_status"])
    op.add_column(
        "discussion_comments",
        sa.Column("moderation_status", sa.String(30), nullable=False, server_default="visible"),
    )
    op.create_index("ix_discussion_comments_moderation_status", "discussion_comments", ["moderation_status"])
    op.add_column("evidence", sa.Column("moderation_status", sa.String(30), nullable=False, server_default="visible"))
    op.create_index("ix_evidence_moderation_status", "evidence", ["moderation_status"])
    op.add_column(
        "evidence_comments",
        sa.Column("moderation_status", sa.String(30), nullable=False, server_default="visible"),
    )
    op.create_index("ix_evidence_comments_moderation_status", "evidence_comments", ["moderation_status"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_summary", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.String(40), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in [
        "reporter_user_id",
        "resource_type",
        "resource_id",
        "target_user_id",
        "reason_code",
        "status",
        "reviewed_by_user_id",
    ]:
        op.create_index(f"ix_reports_{column}", "reports", [column])
    op.create_index("ix_reports_status_created_id", "reports", ["status", "created_at", "id"])

    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_actions_report_id", "moderation_actions", ["report_id"])
    op.create_index("ix_moderation_actions_actor_user_id", "moderation_actions", ["actor_user_id"])
    op.create_index("ix_moderation_actions_action", "moderation_actions", ["action"])


def downgrade() -> None:
    op.drop_table("moderation_actions")
    op.drop_table("reports")
    op.drop_index("ix_evidence_comments_moderation_status", table_name="evidence_comments")
    op.drop_column("evidence_comments", "moderation_status")
    op.drop_index("ix_evidence_moderation_status", table_name="evidence")
    op.drop_column("evidence", "moderation_status")
    op.drop_index("ix_discussion_comments_moderation_status", table_name="discussion_comments")
    op.drop_column("discussion_comments", "moderation_status")
    op.drop_index("ix_users_moderation_status", table_name="users")
    op.drop_column("users", "moderation_status")
