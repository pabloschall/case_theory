"""Persist web research sources and timeline provenance."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0005"
down_revision: str | None = "20260920_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("publisher", sa.String(255)),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("reliability_metadata", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_sources_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("case_id", "canonical_url", name="uq_sources_case_id"),
    )
    op.create_index("ix_sources_case_id", "sources", ["case_id"])
    op.create_table(
        "timeline_event_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timeline_event_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["timeline_event_id"],
            ["timeline_events.id"],
            name="fk_timeline_event_sources_timeline_event_id_timeline_events",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_timeline_event_sources_source_id_sources", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_timeline_event_sources"),
        sa.UniqueConstraint("timeline_event_id", "source_id", name="uq_timeline_event_sources_timeline_event_id"),
    )
    op.create_index("ix_timeline_event_sources_timeline_event_id", "timeline_event_sources", ["timeline_event_id"])
    op.create_index("ix_timeline_event_sources_source_id", "timeline_event_sources", ["source_id"])


def downgrade() -> None:
    op.drop_table("timeline_event_sources")
    op.drop_table("sources")
