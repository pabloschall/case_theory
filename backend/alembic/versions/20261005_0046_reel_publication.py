"""Add automated reel publication state.

Revision ID: 20261005_0046
Revises: 20261005_0045
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261005_0046"
down_revision: str | None = "20261005_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reel_drafts", sa.Column("automated", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reel_drafts", sa.Column("scheduled_slot", sa.String(length=80), nullable=True))
    op.add_column("reel_drafts", sa.Column("video_object_key", sa.String(length=1024), nullable=True))
    op.add_column("reel_drafts", sa.Column("youtube_video_id", sa.String(length=64), nullable=True))
    op.add_column("reel_drafts", sa.Column("youtube_url", sa.String(length=2048), nullable=True))
    op.add_column("reel_drafts", sa.Column("error_message", sa.String(length=1000), nullable=True))
    op.add_column("reel_drafts", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_reel_drafts_scheduled_slot", "reel_drafts", ["scheduled_slot"], unique=True)
    op.create_unique_constraint("uq_reel_drafts_youtube_video_id", "reel_drafts", ["youtube_video_id"])


def downgrade() -> None:
    op.drop_constraint("uq_reel_drafts_youtube_video_id", "reel_drafts", type_="unique")
    op.drop_index("ix_reel_drafts_scheduled_slot", table_name="reel_drafts")
    for column in (
        "published_at",
        "error_message",
        "youtube_url",
        "youtube_video_id",
        "video_object_key",
        "scheduled_slot",
        "automated",
    ):
        op.drop_column("reel_drafts", column)
