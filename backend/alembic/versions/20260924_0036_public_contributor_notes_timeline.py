"""add public contributor notes and personal timeline

Revision ID: 20260924_0036
Revises: 20260924_0035
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260924_0036"
down_revision: str | None = "20260924_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_case_notebook_notes_case_updated_id",
        "case_notebook_notes",
        ["case_id", "updated_at", "id"],
    )
    op.create_table(
        "case_timeline_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_case_timeline_entries_case_date_id",
        "case_timeline_entries",
        ["case_id", "occurred_on", "id"],
    )
    op.create_index(
        "ix_case_timeline_entries_case_id", "case_timeline_entries", ["case_id"]
    )
    op.create_index(
        "ix_case_timeline_entries_author_user_id",
        "case_timeline_entries",
        ["author_user_id"],
    )
    op.create_index(
        "ix_case_timeline_entries_occurred_on",
        "case_timeline_entries",
        ["occurred_on"],
    )
    op.execute(
        sa.text(
            """
            DELETE FROM plan_permissions
            WHERE plan_id = (SELECT id FROM subscription_plans WHERE code = 'free')
              AND permission_id IN (
                  SELECT id FROM permissions WHERE code IN ('notes.write', 'timeline.write')
              )
            """
        )
    )
    op.execute(
        sa.text(
            "UPDATE permissions SET description = "
            "'Create and manage public contributor case notes' "
            "WHERE code = 'notes.write'"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    free_plan_id = connection.scalar(
        sa.text("SELECT id FROM subscription_plans WHERE code = 'free'")
    )
    permission_ids = connection.execute(
        sa.text("SELECT id FROM permissions WHERE code IN ('notes.write', 'timeline.write')")
    ).scalars()
    plan_permissions = sa.table(
        "plan_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("plan_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    if free_plan_id is not None:
        op.bulk_insert(
            plan_permissions,
            [
                {
                    "id": uuid.uuid4(),
                    "plan_id": free_plan_id,
                    "permission_id": permission_id,
                }
                for permission_id in permission_ids
            ],
        )
    op.execute(
        sa.text(
            "UPDATE permissions SET description = "
            "'Create and manage private case notebook notes' "
            "WHERE code = 'notes.write'"
        )
    )
    op.drop_table("case_timeline_entries")
    op.drop_index(
        "ix_case_notebook_notes_case_updated_id", table_name="case_notebook_notes"
    )
