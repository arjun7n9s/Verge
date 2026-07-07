"""Finding telemetry assembly — buffer + optional Timescale overlay."""

from __future__ import annotations

import os

from verge_schema.findings import RiskFinding

from .reading_buffer import ReadingBuffer
from .timescale_writer import query_sensor_series


def telemetry_for_finding(
    buffer: ReadingBuffer,
    finding: RiskFinding,
    *,
    thresholds: dict[str, float] | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """Prefer Timescale series when configured and richer than the ring buffer."""
    env = env or dict(os.environ)
    base = buffer.series_for_finding(finding, thresholds=thresholds)
    sensor_ids = buffer.sensor_ids_for_finding(finding)
    ts_map = query_sensor_series(sensor_ids, env=env)
    if not ts_map:
        return base

    merged = []
    for series in base["series"]:
        sid = series["sensorId"]
        ts_points = ts_map.get(sid)
        if ts_points and len(ts_points) >= len(series["points"]):
            merged.append({**series, "points": ts_points})
        else:
            merged.append(series)

    for sid, points in ts_map.items():
        if sid not in {s["sensorId"] for s in merged}:
            merged.append({
                "sensorId": sid,
                "kind": "unknown",
                "unit": "",
                "threshold": (thresholds or {}).get("unknown"),
                "points": points,
            })

    return {
        **base,
        "series": merged,
        "degraded": len(merged) == 0,
        "reason": None if merged else base.get("reason"),
        "source": "timescale" if ts_map else "buffer",
    }
