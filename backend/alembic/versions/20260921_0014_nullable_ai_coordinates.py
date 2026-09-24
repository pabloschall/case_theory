"""Allow place-name-only AI locations and remove zero placeholders."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0014"
down_revision: str | None = "20260921_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("case_locations", "latitude", existing_type=sa.Float(), nullable=True)
    op.alter_column("case_locations", "longitude", existing_type=sa.Float(), nullable=True)
    op.execute(
        """
        UPDATE case_locations
        SET latitude = NULL, longitude = NULL
        WHERE ai_suggested IS TRUE AND latitude = 0 AND longitude = 0
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM case_locations
        WHERE latitude IS NULL OR longitude IS NULL
        """
    )
    op.alter_column("case_locations", "longitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("case_locations", "latitude", existing_type=sa.Float(), nullable=False)
