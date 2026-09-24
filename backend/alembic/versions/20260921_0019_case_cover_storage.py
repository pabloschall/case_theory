"""Store generated case cover object keys."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0019"
down_revision: str | None = "20260921_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("cover_image_object_key", sa.String(length=1024)))


def downgrade() -> None:
    op.drop_column("cases", "cover_image_object_key")
