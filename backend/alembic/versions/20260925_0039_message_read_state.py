"""Track the last message read by each conversation participant.

Revision ID: 20260925_0039
Revises: 20260925_0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260925_0039"
down_revision: str | None = "20260925_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("direct_conversations", sa.Column("user_one_read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("direct_conversations", sa.Column("user_two_read_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE direct_conversations SET user_one_read_at = updated_at, user_two_read_at = updated_at")


def downgrade() -> None:
    op.drop_column("direct_conversations", "user_two_read_at")
    op.drop_column("direct_conversations", "user_one_read_at")
