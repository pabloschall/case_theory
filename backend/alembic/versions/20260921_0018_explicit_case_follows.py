"""Make following explicit and separate from case ownership."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260921_0018"
down_revision: str | None = "20260921_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM case_followers
        USING cases
        WHERE case_followers.case_id = cases.id
          AND case_followers.user_id = cases.created_by_user_id
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO case_followers (id, case_id, user_id, created_at)
        SELECT gen_random_uuid(), cases.id, cases.created_by_user_id, CURRENT_TIMESTAMP
        FROM cases
        WHERE NOT EXISTS (
            SELECT 1
            FROM case_followers
            WHERE case_followers.case_id = cases.id
              AND case_followers.user_id = cases.created_by_user_id
        )
        """
    )
