"""add private case notebook notes

Revision ID: 20260923_0031
Revises: 20260923_0030
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_0031"
down_revision: str | None = "20260923_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_notebook_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_notebook_notes_case_id", "case_notebook_notes", ["case_id"])
    op.create_index(
        "ix_case_notebook_notes_author_user_id",
        "case_notebook_notes",
        ["author_user_id"],
    )
    op.create_index(
        "ix_case_notebook_notes_owner_case_updated_id",
        "case_notebook_notes",
        ["author_user_id", "case_id", "updated_at", "id"],
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    plans = sa.table(
        "subscription_plans", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    plan_permissions = sa.table(
        "plan_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("plan_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    permission_id = uuid.uuid4()
    op.bulk_insert(
        permissions,
        [
            {
                "id": permission_id,
                "code": "notes.write",
                "description": "Create and manage private case notebook notes",
            }
        ],
    )
    plan_ids = op.get_bind().execute(
        sa.select(plans.c.id).where(plans.c.code.in_(["investigator", "lead", "admin"]))
    )
    op.bulk_insert(
        plan_permissions,
        [
            {
                "id": uuid.uuid4(),
                "plan_id": plan_id,
                "permission_id": permission_id,
            }
            for plan_id in plan_ids.scalars()
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'notes.write'"))
    op.drop_table("case_notebook_notes")
