"""Phase 1 identity, sessions, plans, and permissions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(40), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("bio", sa.Text()),
        sa.Column("avatar_url", sa.String(2048)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_profiles_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_profiles"),
    )
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("active_case_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_ai_run_limit", sa.Integer(), nullable=False),
        sa.Column("storage_bytes_limit", sa.Integer(), nullable=False),
        sa.Column("collaborator_limit", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_subscription_plans"),
        sa.UniqueConstraint("code", name="uq_subscription_plans_code"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_table(
        "plan_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_plan_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            name="fk_plan_permissions_plan_id_subscription_plans",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_plan_permissions"),
        sa.UniqueConstraint("plan_id", "permission_id", name="uq_plan_permissions_plan_id"),
    )
    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["subscription_plans.id"], name="fk_user_subscriptions_plan_id_subscription_plans"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_subscriptions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_subscriptions"),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_refresh_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("refresh_sessions")
    op.drop_table("user_subscriptions")
    op.drop_table("plan_permissions")
    op.drop_table("permissions")
    op.drop_table("subscription_plans")
    op.drop_table("user_profiles")
    op.drop_table("users")
