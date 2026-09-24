"""restore private personal notes and timeline metadata

Revision ID: 20260924_0037
Revises: 20260924_0036
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260924_0037"
down_revision: str | None = "20260924_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE permissions SET description = "
            "'Create and manage private case notebook notes' "
            "WHERE code = 'notes.write'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE permissions SET description = "
            "'Create and manage public contributor case notes' "
            "WHERE code = 'notes.write'"
        )
    )
