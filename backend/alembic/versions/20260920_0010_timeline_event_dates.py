"""Store timeline event dates for chronological ordering."""

import re
from collections.abc import Sequence
from datetime import date

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_0010"
down_revision: str | None = "20260920_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONTHS = {
    name: number
    for number, names in enumerate(
        (
            (),
            ("january", "jan"), ("february", "feb"), ("march", "mar"),
            ("april", "apr"), ("may",), ("june", "jun"), ("july", "jul"),
            ("august", "aug"), ("september", "sep", "sept"),
            ("october", "oct"), ("november", "nov"), ("december", "dec"),
        )
    )
    for name in names
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))


def _parse(value: str) -> date | None:
    normalized = value.strip().lower()
    iso = re.search(r"\b((?:18|19|20)\d{2})-(\d{1,2})-(\d{1,2})\b", normalized)
    if iso:
        try:
            return date(*(int(part) for part in iso.groups()))
        except ValueError:
            return None
    full = re.search(
        rf"\b({MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*[-–]\s*\d{{1,2}})?\s*,?\s*((?:18|19|20)\d{{2}})\b",
        normalized,
    )
    if full:
        month, day, year = full.groups()
        try:
            return date(int(year), MONTHS[month], int(day))
        except ValueError:
            return None
    month = re.search(rf"\b({MONTH_PATTERN})\.?\s+((?:18|19|20)\d{{2}})\b", normalized)
    if month:
        name, year = month.groups()
        return date(int(year), MONTHS[name], 1)
    year = re.search(r"\b((?:18|19|20)\d{2})\b", normalized)
    return date(int(year.group(1)), 1, 1) if year else None


def upgrade() -> None:
    op.add_column("timeline_events", sa.Column("occurred_on", sa.Date(), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, date_label FROM timeline_events")).mappings()
    for row in rows:
        occurred_on = _parse(row["date_label"])
        if occurred_on:
            connection.execute(
                sa.text("UPDATE timeline_events SET occurred_on = :occurred_on WHERE id = :id"),
                {"occurred_on": occurred_on, "id": row["id"]},
            )
    op.create_index("ix_timeline_events_occurred_on", "timeline_events", ["occurred_on"])


def downgrade() -> None:
    op.drop_index("ix_timeline_events_occurred_on", table_name="timeline_events")
    op.drop_column("timeline_events", "occurred_on")
