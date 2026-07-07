"""In-memory sensor reading ring buffer with optional SQL persistence (M9)."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, insert, select
from sqlalchemy.engine import Engine
from verge_schema.findings import RiskFinding

from . import db

REPLAY_SEED = Path(__file__).resolve().parents[3] / "eval/replays/vizag-2025-01/events.jsonl"
MAX_POINTS_PER_SENSOR = 120


class ReadingBuffer:
    """Rolling window of canonical reading events keyed by sensor_id."""

    def __init__(
        self,
        engine: Engine | None = None,
        max_points: int = MAX_POINTS_PER_SENSOR,
    ) -> None:
        self._max = max_points
        self._by_sensor: dict[str, deque[dict]] = defaultdict(deque)
        self._engine = engine
        if engine is not None:
            self._hydrate_from_db()

    def _hydrate_from_db(self) -> None:
        with self._engine.begin() as conn:  # type: ignore[union-attr]
            rows = conn.execute(
                select(db.sensor_reading).order_by(db.sensor_reading.c.ts)
            ).mappings().all()
        for row in rows:
            self._append_point(
                row["sensor_id"],
                {
                    "ts": row["ts"].isoformat() if isinstance(row["ts"], datetime) else row["ts"],
                    "value": float(row["value"]),
                    "zoneId": row["zone_id"],
                    "kind": row["kind"],
                    "unit": row["unit"],
                },
                persist=False,
            )

    def _append_point(self, sensor_id: str, point: dict, *, persist: bool) -> None:
        buf = self._by_sensor[sensor_id]
        buf.append(point)
        while len(buf) > self._max:
            buf.popleft()
        if persist:
            self._persist_reading(sensor_id, point)

    def _persist_reading(self, sensor_id: str, point: dict) -> None:
        if self._engine is None:
            return
        ts = datetime.fromisoformat(point["ts"])
        with self._engine.begin() as conn:
            conn.execute(
                insert(db.sensor_reading).values(
                    sensor_id=sensor_id,
                    ts=ts,
                    value=point["value"],
                    zone_id=point.get("zoneId"),
                    kind=point.get("kind"),
                    unit=point.get("unit"),
                )
            )
            # Trim old rows per sensor to keep the DB bounded.
            rows = conn.execute(
                select(db.sensor_reading.c.id)
                .where(db.sensor_reading.c.sensor_id == sensor_id)
                .order_by(db.sensor_reading.c.ts.desc())
            ).scalars().all()
            if len(rows) > self._max:
                stale = rows[self._max :]
                conn.execute(
                    delete(db.sensor_reading).where(db.sensor_reading.c.id.in_(stale))
                )

    def ingest(self, event: dict) -> None:
        if event.get("type") != "reading":
            return
        sensor_id = event.get("sensorId")
        if not sensor_id:
            return
        point = {
            "ts": event["ts"],
            "value": float(event["value"]),
            "zoneId": event.get("zoneId"),
            "kind": event.get("kind"),
            "unit": event.get("unit"),
        }
        self._append_point(sensor_id, point, persist=True)

    def seed_from_replay(self, path: Path | None = None) -> int:
        path = path or REPLAY_SEED
        if not path.exists():
            return 0
        if self._engine is not None and self._by_sensor:
            return sum(len(v) for v in self._by_sensor.values())
        n = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("type") == "reading":
                self.ingest(event)
                n += 1
        return n

    def sensor_count(self) -> int:
        """Number of distinct sensors seen (plant-IT ingest health, §14.6)."""
        return len(self._by_sensor)

    def reading_count(self) -> int:
        """Total buffered reading points across all sensors."""
        return sum(len(buf) for buf in self._by_sensor.values())

    def latest_ts(self) -> str | None:
        """ISO timestamp of the most recent buffered reading, or None if empty."""
        latest: str | None = None
        for buf in self._by_sensor.values():
            if buf:
                ts = buf[-1].get("ts")
                if ts and (latest is None or ts > latest):
                    latest = ts
        return latest

    def sensor_ids_for_finding(self, finding: RiskFinding) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for ref in finding.lineage:
            if ref.startswith("reading:"):
                sid = ref.split(":", 1)[1]
                if sid not in seen:
                    seen.add(sid)
                    ids.append(sid)
        for sig in finding.contributing_signals:
            if sig.kind == "reading" and sig.ref_id not in seen:
                seen.add(sig.ref_id)
                ids.append(sig.ref_id)
        if not ids:
            for sid, buf in self._by_sensor.items():
                if buf and buf[-1].get("zoneId") == finding.zone_id:
                    ids.append(sid)
        return ids

    def series_for_finding(
        self,
        finding: RiskFinding,
        *,
        thresholds: dict[str, float] | None = None,
    ) -> dict:
        thresholds = thresholds or {}
        sensor_ids = self.sensor_ids_for_finding(finding)
        series = []
        for sid in sensor_ids:
            points = list(self._by_sensor.get(sid, []))
            if not points:
                continue
            kind = points[-1].get("kind") or "unknown"
            series.append({
                "sensorId": sid,
                "kind": kind,
                "unit": points[-1].get("unit") or "",
                "threshold": thresholds.get(kind),
                "points": points,
            })
        return {
            "findingId": finding.finding_id,
            "zoneId": finding.zone_id,
            "series": series,
            "degraded": len(series) == 0,
            "reason": None if series else "no telemetry for finding sensors",
        }
