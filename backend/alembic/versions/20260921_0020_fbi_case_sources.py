"""Add reusable external case sources and field provenance."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260921_0020"
down_revision: str | None = "20260921_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "timeline_events",
        sa.Column("date_precision", sa.String(length=30), nullable=False, server_default="unknown"),
    )
    op.create_table(
        "case_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_published_at", sa.DateTime(timezone=True)),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "external_id"),
    )
    op.create_index("ix_case_sources_case_id", "case_sources", ["case_id"])
    op.create_index("ix_case_sources_source_type", "case_sources", ["source_type"])
    op.create_index("ix_case_sources_external_id", "case_sources", ["external_id"])
    op.create_table(
        "source_citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_source_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("source_field", sa.String(length=120), nullable=False),
        sa.Column("source_text", sa.Text()),
        sa.Column("interpretation_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_source_id"], ["case_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_citations_case_source_id", "source_citations", ["case_source_id"])
    op.create_index("ix_source_citations_resource_type", "source_citations", ["resource_type"])
    op.create_index("ix_source_citations_resource_id", "source_citations", ["resource_id"])


def downgrade() -> None:
    op.drop_table("source_citations")
    op.drop_table("case_sources")
    op.drop_column("timeline_events", "date_precision")
