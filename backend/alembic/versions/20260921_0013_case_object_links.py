"""Link people and evidence to case objects."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0013"
down_revision: str | None = "20260921_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _link_table(
    name: str,
    parent_column: str,
    parent_table: str,
    target_column: str,
    target_table: str,
) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(parent_column, sa.Uuid(), nullable=False),
        sa.Column(target_column, sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint([parent_column], [f"{parent_table}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint([target_column], [f"{target_table}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(parent_column, target_column),
    )
    op.create_index(f"ix_{name}_{parent_column}", name, [parent_column])
    op.create_index(f"ix_{name}_{target_column}", name, [target_column])
    op.create_index(f"ix_{name}_created_by_user_id", name, ["created_by_user_id"])


def upgrade() -> None:
    _link_table("timeline_event_people", "timeline_event_id", "timeline_events", "person_id", "people")
    _link_table("discussion_thread_people", "thread_id", "discussion_threads", "person_id", "people")
    _link_table("case_location_evidence", "location_id", "case_locations", "evidence_id", "evidence")
    _link_table("case_location_people", "location_id", "case_locations", "person_id", "people")


def downgrade() -> None:
    op.drop_table("case_location_people")
    op.drop_table("case_location_evidence")
    op.drop_table("discussion_thread_people")
    op.drop_table("timeline_event_people")
