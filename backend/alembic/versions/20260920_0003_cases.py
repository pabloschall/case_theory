"""Create the initial case generation vertical slice."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0003"
down_revision: str | None = "20260920_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("victim_names", sa.String(500), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(300), nullable=False),
        sa.Column("intake_notes", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("privacy", sa.String(30), nullable=False),
        sa.Column("ai_research_status", sa.String(30), nullable=False),
        sa.Column("ai_error_message", sa.String(500)),
        sa.Column("cover_image_url", sa.String(2048)),
        sa.Column("cover_image_prompt", sa.Text()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_cases_created_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_cases"),
    )
    op.create_index("ix_cases_created_by_user_id", "cases", ["created_by_user_id"])
    op.create_index("ix_cases_public_id", "cases", ["public_id"], unique=True)
    op.create_index("ix_cases_slug", "cases", ["slug"], unique=True)
    op.create_table(
        "case_followers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_case_followers_case_id_cases", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_case_followers_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_case_followers"),
        sa.UniqueConstraint("case_id", "user_id", name="uq_case_followers_case_id"),
    )
    op.create_index("ix_case_followers_case_id", "case_followers", ["case_id"])
    op.create_index("ix_case_followers_user_id", "case_followers", ["user_id"])
    op.create_table(
        "case_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("ai_model", sa.String(100)),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_case_summaries_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_case_summaries"),
    )
    op.create_index("ix_case_summaries_case_id", "case_summaries", ["case_id"])
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("date_label", sa.String(120), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("source_note", sa.String(500), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_timeline_events_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_timeline_events"),
    )
    op.create_index("ix_timeline_events_case_id", "timeline_events", ["case_id"])
    op.create_table(
        "case_generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("text_model", sa.String(100)),
        sa.Column("image_model", sa.String(100)),
        sa.Column("error_message", sa.String(500)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name="fk_case_generation_jobs_case_id_cases", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_case_generation_jobs"),
    )
    op.create_index("ix_case_generation_jobs_case_id", "case_generation_jobs", ["case_id"])


def downgrade() -> None:
    op.drop_table("case_generation_jobs")
    op.drop_table("timeline_events")
    op.drop_table("case_summaries")
    op.drop_table("case_followers")
    op.drop_table("cases")
