"""Record authorship for user-created timeline events."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0008"
down_revision: str | None = "20260920_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("timeline_events", sa.Column("created_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_timeline_events_created_by_user_id_users",
        "timeline_events",
        "users",
        ["created_by_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_timeline_events_created_by_user_id",
        "timeline_events",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_timeline_events_created_by_user_id", table_name="timeline_events")
    op.drop_constraint(
        "fk_timeline_events_created_by_user_id_users",
        "timeline_events",
        type_="foreignkey",
    )
    op.drop_column("timeline_events", "created_by_user_id")
