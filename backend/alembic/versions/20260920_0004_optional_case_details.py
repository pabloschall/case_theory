"""Allow cases without a year or location."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260920_0004"
down_revision: str | None = "20260920_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("cases", "year", nullable=True)
    op.alter_column("cases", "location", nullable=True)


def downgrade() -> None:
    op.alter_column("cases", "location", nullable=False)
    op.alter_column("cases", "year", nullable=False)
