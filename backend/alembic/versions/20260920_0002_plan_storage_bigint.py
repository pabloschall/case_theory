"""Use bigint for plan storage byte limits."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0002"
down_revision: str | None = "20260920_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("subscription_plans", "storage_bytes_limit", existing_type=sa.Integer(), type_=sa.BigInteger())


def downgrade() -> None:
    op.alter_column("subscription_plans", "storage_bytes_limit", existing_type=sa.BigInteger(), type_=sa.Integer())
