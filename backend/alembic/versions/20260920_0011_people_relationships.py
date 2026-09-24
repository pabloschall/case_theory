"""Add people, relationships, evidence links, and notes."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0011"
down_revision: str | None = "20260920_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("slug", sa.String(280), nullable=False),
        sa.Column("role", sa.String(120), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("photo_url", sa.String(2048)),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("place_of_birth", sa.String(300)),
        sa.Column("relationship_to_primary", sa.String(240)),
        sa.Column("summary", sa.Text()),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("ai_suggested", sa.Boolean(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "slug"),
    )
    op.create_index("ix_people_case_id", "people", ["case_id"])
    op.create_index("ix_people_category", "people", ["category"])
    op.create_index("ix_people_created_by_user_id", "people", ["created_by_user_id"])
    op.create_table(
        "person_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("source_person_id", sa.Uuid(), nullable=False),
        sa.Column("target_person_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("source_type", sa.String(40)),
        sa.Column("source_id", sa.Uuid()),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("ai_suggested", sa.Boolean(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_person_id", "target_person_id", "relationship_type"),
    )
    for column in ("case_id", "source_person_id", "target_person_id", "source_id", "created_by_user_id"):
        op.create_index(f"ix_person_relationships_{column}", "person_relationships", [column])
    op.create_table(
        "person_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", "evidence_id"),
    )
    op.create_index("ix_person_evidence_person_id", "person_evidence", ["person_id"])
    op.create_index("ix_person_evidence_evidence_id", "person_evidence", ["evidence_id"])
    op.create_index("ix_person_evidence_created_by_user_id", "person_evidence", ["created_by_user_id"])
    op.create_table(
        "person_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_person_notes_person_id", "person_notes", ["person_id"])
    op.create_index("ix_person_notes_author_user_id", "person_notes", ["author_user_id"])


def downgrade() -> None:
    op.drop_table("person_notes")
    op.drop_table("person_evidence")
    op.drop_table("person_relationships")
    op.drop_table("people")
