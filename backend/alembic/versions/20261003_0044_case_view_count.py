"""Add a view count to cases.

Revision ID: 20261003_0044
Revises: 20260926_0043
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261003_0044"
down_revision: str | None = "20260926_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("view_count", sa.BigInteger(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("cases", "view_count")
