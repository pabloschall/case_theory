"""Add sourced AI link evidence metadata."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0016"
down_revision: str | None = "20260921_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("source_id", sa.Uuid(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "evidence",
        sa.Column("review_status", sa.String(30), server_default="published", nullable=False),
    )
    op.create_foreign_key(
        "fk_evidence_source_id_sources",
        "evidence",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_evidence_source_id", "evidence", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_source_id", table_name="evidence")
    op.drop_constraint("fk_evidence_source_id_sources", "evidence", type_="foreignkey")
    op.drop_column("evidence", "review_status")
    op.drop_column("evidence", "ai_generated")
    op.drop_column("evidence", "source_id")
