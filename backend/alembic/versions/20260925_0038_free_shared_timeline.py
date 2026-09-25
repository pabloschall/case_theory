"""allow free accounts to add shared timeline events

Revision ID: 20260925_0038
Revises: 20260924_0037
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925_0038"
down_revision: str | None = "20260924_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    private_permission_id = connection.scalar(
        sa.text("SELECT id FROM permissions WHERE code = 'timeline.private_write'")
    )
    if private_permission_id is None:
        private_permission_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO permissions (id, code, description) "
                "VALUES (:id, 'timeline.private_write', "
                "'Create and manage private personal timeline entries')"
            ),
            {"id": private_permission_id},
        )

    connection.execute(
        sa.text(
            "INSERT INTO plan_permissions (id, plan_id, permission_id) "
            "SELECT :id, plan.id, permission.id "
            "FROM subscription_plans AS plan "
            "JOIN permissions AS permission ON permission.code = 'timeline.write' "
            "WHERE plan.code = 'free' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM plan_permissions existing "
            "  WHERE existing.plan_id = plan.id "
            "  AND existing.permission_id = permission.id"
            ")"
        ),
        {"id": uuid.uuid4()},
    )
    for plan_code in ("investigator", "lead", "admin"):
        connection.execute(
            sa.text(
                "INSERT INTO plan_permissions (id, plan_id, permission_id) "
                "SELECT :id, plan.id, :permission_id "
                "FROM subscription_plans AS plan "
                "WHERE plan.code = :plan_code "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM plan_permissions existing "
                "  WHERE existing.plan_id = plan.id "
                "  AND existing.permission_id = :permission_id"
                ")"
            ),
            {
                "id": uuid.uuid4(),
                "permission_id": private_permission_id,
                "plan_code": plan_code,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM plan_permissions "
            "WHERE plan_id = (SELECT id FROM subscription_plans WHERE code = 'free') "
            "AND permission_id = (SELECT id FROM permissions WHERE code = 'timeline.write')"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM plan_permissions "
            "WHERE permission_id = ("
            "  SELECT id FROM permissions WHERE code = 'timeline.private_write'"
            ")"
        )
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = 'timeline.private_write'"))
