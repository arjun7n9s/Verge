"""Initial durable store schema (mirrors verge_api/db.py).

Revision ID: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finding",
        sa.Column("finding_id", sa.String(), primary_key=True),
        sa.Column("zone_id", sa.String(), index=True),
        sa.Column("state", sa.String(), index=True),
        sa.Column("shadow", sa.Boolean(), index=True, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), index=True),
        sa.Column("data", sa.JSON()),
    )
    op.create_table(
        "finding_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.String(), index=True),
        sa.Column("actor", sa.String()),
        sa.Column("verdict", sa.String()),
        sa.Column("reason_code", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "audit_entry",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.String(), unique=True),
        sa.Column("ts", sa.String()),
        sa.Column("actor", sa.String()),
        sa.Column("kind", sa.String()),
        sa.Column("payload", sa.JSON()),
        sa.Column("hash", sa.String()),
        sa.Column("prev_hash", sa.String(), nullable=True),
    )
    op.create_table(
        "sensor_health",
        sa.Column("quality", sa.String(), primary_key=True),
        sa.Column("count", sa.Integer()),
    )
    op.create_table(
        "permit",
        sa.Column("permit_id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("zone_id", sa.String(), nullable=False, index=True),
        sa.Column("equipment_id", sa.String(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
    )
    op.create_table(
        "sensor_reading",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sensor_id", sa.String(), index=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("zone_id", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sensor_reading")
    op.drop_table("permit")
    op.drop_table("sensor_health")
    op.drop_table("audit_entry")
    op.drop_table("finding_feedback")
    op.drop_table("finding")
