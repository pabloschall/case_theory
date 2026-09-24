"""Add sourced case locations."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0012"
down_revision: str | None = "20260920_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_type", sa.String(40), nullable=False),
        sa.Column("occurred_on", sa.Date()),
        sa.Column("precision", sa.String(30), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("source_id", sa.Uuid()),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("ai_suggested", sa.Boolean(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("case_id", "location_type", "occurred_on", "source_id", "created_by_user_id"):
        op.create_index(f"ix_case_locations_{column}", "case_locations", [column])


def downgrade() -> None:
    op.drop_table("case_locations")
