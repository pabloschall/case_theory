"""Add case, source scout, and evidence connection badges.

Revision ID: 20260925_0041
Revises: 20260925_0040
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925_0041"
down_revision: str | None = "20260925_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    rules = sa.table(
        "progression_rules",
        sa.column("code", sa.String),
        sa.column("reason", sa.String),
        sa.column("xp", sa.Integer),
        sa.column("daily_cap", sa.Integer),
        sa.column("lifetime_once", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        rules,
        [
            {
                "code": "case_created",
                "reason": "First case file opened",
                "xp": 0,
                "daily_cap": None,
                "lifetime_once": True,
                "is_active": True,
            },
            {
                "code": "evidence_person_linked",
                "reason": "Evidence linked to a person",
                "xp": 4,
                "daily_cap": 20,
                "lifetime_once": False,
                "is_active": True,
            },
        ],
    )
    badges = sa.table(
        "badge_definitions",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("criteria", sa.Text),
        sa.column("category", sa.String),
        sa.column("icon_key", sa.String),
        sa.column("criteria_version", sa.Integer),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        badges,
        [
            {
                "code": "case_file_opened",
                "name": "Case File Opened",
                "description": "You opened your first Case Theory case file.",
                "criteria": "Create your first case.",
                "category": "research_craft",
                "icon_key": "case-file",
                "criteria_version": 1,
                "sort_order": 4,
                "is_active": True,
            },
            {
                "code": "source_scout",
                "name": "Source Scout",
                "description": "You found reliable public sources across several cases.",
                "criteria": "Add 10 qualifying public evidence links across at least 3 cases.",
                "category": "research_craft",
                "icon_key": "compass",
                "criteria_version": 1,
                "sort_order": 5,
                "is_active": True,
            },
            {
                "code": "first_connection",
                "name": "First Connection",
                "description": "You connected evidence to a person for the first time.",
                "criteria": "Link an evidence item to a person.",
                "category": "research_craft",
                "icon_key": "connection",
                "criteria_version": 1,
                "sort_order": 6,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM user_badges "
            "WHERE badge_code IN ('case_file_opened', 'source_scout', 'first_connection')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM badge_definitions "
            "WHERE code IN ('case_file_opened', 'source_scout', 'first_connection')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM progression_ledger "
            "WHERE rule_code IN ('case_created', 'evidence_person_linked')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM progression_rules "
            "WHERE code IN ('case_created', 'evidence_person_linked')"
        )
    )
