"""The three baselines Verge must beat (spec §10.3).

Each returns the first alert timestamp (or None). They see only sensor readings
+ thresholds — no permits, no shift state, no graph. That blindness is the point.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from verge_schema.core import Reading, Sensor


def b0_fixed_threshold(
    readings: dict[str, list[Reading]], sensors: dict[str, Sensor], thresholds: dict[str, float]
) -> datetime | None:
    """B0 — alert iff any single sensor crosses its fixed threshold. The strawman."""
    first: datetime | None = None
    for sid, reads in readings.items():
        thr = thresholds.get(sensors[sid].kind)
        if thr is None:
            continue
        for r in reads:
            if r.value >= thr:
                first = r.ts if first is None else min(first, r.ts)
                break
    return first


def b1_rate_of_rise(
    readings: dict[str, list[Reading]],
    sensors: dict[str, Sensor],
    thresholds: dict[str, float],
    *,
    rate_per_min: float = 2.0,
    window: int = 5,
) -> datetime | None:
    """B1 — alert iff a single sensor's rate-of-change exceeds a fixed ppm/min.
    The *serious* baseline: what a competent DCS engineer would configure."""
    first: datetime | None = None
    for reads in readings.values():
        for i in range(window, len(reads) + 1):
            w = reads[i - window : i]
            dt_min = (w[-1].ts - w[0].ts).total_seconds() / 60.0
            if dt_min <= 0:
                continue
            slope = (w[-1].value - w[0].value) / dt_min
            if slope >= rate_per_min:
                first = w[-1].ts if first is None else min(first, w[-1].ts)
                break
    return first


def b2_multi_sensor_and_gate(
    readings: dict[str, list[Reading]],
    sensors: dict[str, Sensor],
    thresholds: dict[str, float],
    *,
    n_required: int = 2,
    window_min: float = 5.0,
) -> datetime | None:
    """B2 — alert iff N sensors in the same zone cross threshold within T minutes.
    A naive compound check, but with no temporal/lead reasoning."""
    # crossing time per sensor
    crossed: dict[str, tuple[str, datetime]] = {}
    for sid, reads in readings.items():
        thr = thresholds.get(sensors[sid].kind)
        if thr is None:
            continue
        for r in reads:
            if r.value >= thr:
                crossed[sid] = (sensors[sid].zone_id, r.ts)
                break
    # group by zone, find earliest window with >= n_required crossings
    by_zone: dict[str, list[datetime]] = {}
    for _sid, (zone, ts) in crossed.items():
        by_zone.setdefault(zone, []).append(ts)
    best: datetime | None = None
    for times in by_zone.values():
        times.sort()
        for i in range(len(times)):
            within = [t for t in times if t - times[i] <= timedelta(minutes=window_min)]
            if len(within) >= n_required:
                cand = within[n_required - 1]
                best = cand if best is None else min(best, cand)
                break
    return best
