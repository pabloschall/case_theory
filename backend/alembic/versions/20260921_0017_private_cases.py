"""Add private-case permission for paid subscription plans."""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_0017"
down_revision: str | None = "20260921_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    plans = sa.table(
        "subscription_plans",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    plan_permissions = sa.table(
        "plan_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("plan_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    permission_id = uuid.uuid4()
    op.bulk_insert(
        permissions,
        [
            {
                "id": permission_id,
                "code": "case.private",
                "description": "Create and manage private cases",
            }
        ],
    )
    paid_plans = op.get_bind().execute(
        sa.select(plans.c.id).where(plans.c.code.in_(["investigator", "lead", "admin"]))
    )
    op.bulk_insert(
        plan_permissions,
        [
            {
                "id": uuid.uuid4(),
                "plan_id": plan_id,
                "permission_id": permission_id,
            }
            for plan_id in paid_plans.scalars()
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'case.private'"))
