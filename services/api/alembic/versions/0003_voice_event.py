"""Durable voice events for fusion across restarts.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_event",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("transcript", sa.String(), nullable=False, server_default=""),
        sa.Column("transcript_original", sa.String(), nullable=True),
        sa.Column("languages_detected", sa.JSON(), nullable=False),
        sa.Column("zone_id", sa.String(), nullable=True, index=True),
        sa.Column("hazards", sa.JSON(), nullable=False),
        sa.Column("equipment_ids", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="radio"),
    )


def downgrade() -> None:
    op.drop_table("voice_event")
