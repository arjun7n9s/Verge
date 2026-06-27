"""Deterministic generator for a synthetic near-miss (spec §10.1 row 4).

Fully synthetic and documented (not a real incident): a confined-space entry
with rising toxic gas (CO) that Verge catches early enough for the operator to
act — the no-breach case. We still record a `breachTs` (the projected crossing
had no one intervened) so lead time is computed consistently across replays.

Assumptions:
- Zone CS-7 (confined space). Confined-space permit (PW-CS-0007) active.
- CO-CS drifts from ~30 ppm (~0.8 ppm/min) toward the 50 ppm alarm, projected
  to cross at ~+25 min. Single sensor (multi-sensor AND-gate B2 stays silent).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
T0 = datetime(2025, 6, 1, 9, 0, tzinfo=UTC)
BREACH = T0 + timedelta(minutes=25)
CO_THRESHOLD = 50.0


def _iso(t: datetime) -> str:
    return t.isoformat()


def _co(m: float) -> float:
    return round(30.0 + 0.8 * m, 2)


def build_events() -> list[dict]:
    events: list[dict] = [{
        "type": "permit", "ts": _iso(T0 + timedelta(minutes=6)),
        "permitId": "PW-CS-0007", "kind": "confined-space", "zoneId": "CS-7",
        "equipmentId": "vessel-V-12",
        "validFrom": _iso(T0 + timedelta(minutes=6)),
        "validTo": _iso(BREACH + timedelta(minutes=30)),
    }]
    t, end = T0, BREACH + timedelta(minutes=5)
    while t <= end:
        m = (t - T0).total_seconds() / 60.0
        events.append({"type": "reading", "ts": _iso(t), "sensorId": "CO-CS",
                       "kind": "gas-co", "unit": "ppm", "zoneId": "CS-7", "value": _co(m)})
        t += timedelta(seconds=30)
    return events


def build_ground_truth() -> dict:
    return {
        "incidentId": "synthetic-nearmiss-01",
        "title": "Confined-space entry with rising CO (synthetic near-miss)",
        "zoneId": "CS-7",
        "breachTs": _iso(BREACH),
        "thresholdSensor": "CO-CS",
        "thresholds": {"gas-co": CO_THRESHOLD},
        "expectedConvergence": ["confined-space permit", "rising toxic gas"],
        "outcome": "near-miss — operator acted before breach",
        "source": "Fully synthetic, documented (not a real incident)",
    }


def build_feedback() -> list[dict]:
    base = {"actor": "operator", "timestamp": _iso(BREACH)}
    return [
        {**base, "findingId": "seed-1", "verdict": "useful"},
        {**base, "findingId": "seed-2", "verdict": "useful"},
    ]


def main() -> None:
    (HERE / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in build_events()) + "\n", encoding="utf-8")
    (HERE / "ground-truth.json").write_text(
        json.dumps(build_ground_truth(), indent=2) + "\n", encoding="utf-8")
    (HERE / "feedback.jsonl").write_text(
        "\n".join(json.dumps(e) for e in build_feedback()) + "\n", encoding="utf-8")
    print(f"wrote replay to {HERE}")


if __name__ == "__main__":
    main()
