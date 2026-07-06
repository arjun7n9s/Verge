"""SQLAlchemy Core schema for the durable store.

Dialect-agnostic types (JSON/String/DateTime/Float/Boolean) so the identical
code runs on SQLite (tests, no Docker) and Postgres (production). The audit
chain's integrity is enforced in application code (verge_audit), not by the DB,
so it holds on either backend.

This owns its own tables (checkfirst=True); a real deployment would manage
migrations with Alembic — noted as future work, not blocking Horizon 0.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

finding = Table(
    "finding", metadata,
    Column("finding_id", String, primary_key=True),
    Column("zone_id", String, index=True),
    Column("state", String, index=True),
    Column("shadow", Boolean, index=True, default=False),
    Column("created_at", DateTime(timezone=True), index=True),
    Column("data", JSON),  # full RiskFinding (camelCase) — the source of truth
)

finding_feedback = Table(
    "finding_feedback", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("finding_id", String, index=True),
    Column("actor", String),
    Column("verdict", String),
    Column("reason_code", String, nullable=True),
    Column("timestamp", DateTime(timezone=True)),
)

audit_entry = Table(
    "audit_entry", metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True),  # chain order
    Column("entry_id", String, unique=True),
    # ISO string, not DateTime: the timestamp is part of the hashed body, and
    # SQLite drops tzinfo from DateTime — which would change the serialization on
    # reload and break chain verification. Storing the exact ISO string keeps the
    # rebuilt chain bit-identical across restarts (P6).
    Column("ts", String),
    Column("actor", String),
    Column("kind", String),
    Column("payload", JSON),
    Column("hash", String),
    Column("prev_hash", String, nullable=True),
)

sensor_health = Table(
    "sensor_health", metadata,
    Column("quality", String, primary_key=True),
    Column("count", Integer),
)

permit = Table(
    "permit", metadata,
    Column("permit_id", String, primary_key=True),
    Column("kind", String, nullable=False),
    Column("zone_id", String, nullable=False, index=True),
    Column("equipment_id", String, nullable=True),
    Column("valid_from", DateTime(timezone=True), nullable=False),
    Column("valid_to", DateTime(timezone=True), nullable=False),
    Column("status", String, nullable=False, default="open"),
)

sensor_reading = Table(
    "sensor_reading", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sensor_id", String, index=True, nullable=False),
    Column("ts", DateTime(timezone=True), index=True, nullable=False),
    Column("value", Float, nullable=False),
    Column("zone_id", String, nullable=True),
    Column("kind", String, nullable=True),
    Column("unit", String, nullable=True),
)


def make_engine(url: str) -> Engine:
    # check_same_thread=False lets the SQLite test/dev engine be shared by the
    # API's threads (TestClient/uvicorn). No effect on Postgres.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, future=True, connect_args=connect_args)
    metadata.create_all(engine, checkfirst=True)
    return engine
