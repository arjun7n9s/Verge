"""Deterministic generator for the Vizag 2025-01 replay (spec §10.1).

IMPORTANT (spec §10): this is a *reconstruction*, not ground truth. Public
reports give a narrative timeline, not per-sensor time-series. This script
encodes documented synthesis assumptions so the events.jsonl it produces is
defensible and reproducible — not extracted.

Assumptions encoded here:
- Zone B-04 coke-oven battery. A hot-work permit (PW-2025-0142) is opened at
  06:40 for the charging-car hydraulic line.
- Shift changeover window 06:42–07:00 (handover blind spot).
- LEL-04 (flammable gas, %LEL) drifts upward from ~80, with mild acceleration
  near the end, crossing the 100 %LEL alarm at ~07:05 (the breach).
- CO-04 (toxic gas) drifts in parallel but crosses its alarm later.
- Injected sensor-health degradation (§10.5): LEL-04 goes stale for 4 minutes
  at 06:38–06:42, exercising the health plane before the convergence.

Run: python -m eval.replays.vizag_2025_01.generate  (or directly).
Outputs (committed): events.jsonl, ground-truth.json, feedback.jsonl
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
T0 = datetime(2025, 1, 13, 6, 30, tzinfo=timezone.utc)
BREACH = datetime(2025, 1, 13, 7, 5, tzinfo=timezone.utc)
LEL_THRESHOLD = 100.0
CO_THRESHOLD = 50.0


def _iso(t: datetime) -> str:
    return t.isoformat()


def _lel_value(t: datetime) -> float:
    """Drift from 80 to ~100 over 35 min, with mild acceleration in the last 8 min."""
    m = (t - T0).total_seconds() / 60.0
    base = 80.0 + 0.45 * m
    accel = 0.06 * max(0.0, m - 27.0) ** 2
    return round(base + accel, 2)


def _co_value(t: datetime) -> float:
    m = (t - T0).total_seconds() / 60.0
    return round(38.0 + 0.32 * m, 2)


def build_events() -> list[dict]:
    events: list[dict] = []

    # Permit opened 06:40
    events.append({
        "type": "permit",
        "ts": _iso(T0 + timedelta(minutes=10)),
        "permitId": "PW-2025-0142",
        "kind": "hot-work",
        "zoneId": "B-04",
        "equipmentId": "charging-car-hydraulics",
        "validFrom": _iso(T0 + timedelta(minutes=10)),
        "validTo": _iso(BREACH + timedelta(minutes=30)),
    })

    # Shift changeover 06:42–07:00
    events.append({"type": "shift", "ts": _iso(T0 + timedelta(minutes=12)),
                   "event": "changeover-start", "zoneId": "B-04"})
    events.append({"type": "shift", "ts": _iso(T0 + timedelta(minutes=30)),
                   "event": "changeover-end", "zoneId": "B-04"})

    # Sensor readings every 30s from T0 to breach+5min
    t = T0
    end = BREACH + timedelta(minutes=5)
    while t <= end:
        # Injected degradation: LEL-04 stale 06:38–06:42 (no readings emitted)
        stale_gap = (T0 + timedelta(minutes=8)) <= t < (T0 + timedelta(minutes=12))
        if not stale_gap:
            events.append({"type": "reading", "ts": _iso(t), "sensorId": "LEL-04",
                           "kind": "gas-lel", "unit": "%LEL", "zoneId": "B-04",
                           "value": _lel_value(t)})
        events.append({"type": "reading", "ts": _iso(t), "sensorId": "CO-04",
                       "kind": "gas-co", "unit": "ppm", "zoneId": "B-04",
                       "value": _co_value(t)})
        t += timedelta(seconds=30)

    return events


def build_ground_truth() -> dict:
    return {
        "incidentId": "vizag-2025-01",
        "title": "Visakhapatnam Steel Plant coke-oven gas incident (reconstructed)",
        "zoneId": "B-04",
        "breachTs": _iso(BREACH),
        "thresholdSensor": "LEL-04",
        "thresholds": {"gas-lel": LEL_THRESHOLD, "gas-co": CO_THRESHOLD},
        "expectedConvergence": ["hot-work permit", "rising flammable gas", "shift changeover"],
        "injectedHealth": [{"sensorId": "LEL-04", "state": "stale", "from": "06:38", "to": "06:42"}],
        "source": "The Wire investigation + public DGFASLI summary (synthesis, not extraction)",
    }


def build_feedback() -> list[dict]:
    """Synthetic operator feedback seeding the FPR calc pre-pilot (spec §10.5).
    Real feedback replaces this in Horizon 1. 1 false alarm out of 5 -> FPR 0.20."""
    base = {"actor": "maya", "timestamp": _iso(BREACH)}
    return [
        {**base, "findingId": "seed-1", "verdict": "useful"},
        {**base, "findingId": "seed-2", "verdict": "useful"},
        {**base, "findingId": "seed-3", "verdict": "useful"},
        {**base, "findingId": "seed-4", "verdict": "useful"},
        {**base, "findingId": "seed-5", "verdict": "false-alarm", "reasonCode": "noise"},
    ]


def main() -> None:
    (HERE / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in build_events()) + "\n", encoding="utf-8"
    )
    (HERE / "ground-truth.json").write_text(
        json.dumps(build_ground_truth(), indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "feedback.jsonl").write_text(
        "\n".join(json.dumps(e) for e in build_feedback()) + "\n", encoding="utf-8"
    )
    print(f"wrote events.jsonl, ground-truth.json, feedback.jsonl to {HERE}")


if __name__ == "__main__":
    main()
