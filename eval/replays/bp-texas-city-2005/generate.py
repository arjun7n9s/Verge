"""Deterministic generator for the BP Texas City 2005 replay (spec §10.1).

RECONSTRUCTION, not ground truth (spec §10). The CSB final report gives a
narrative timeline (raffinate splitter overfill during startup, hydrocarbon
release, ignition near a blowdown stack), NOT per-sensor time-series. This
encodes documented synthesis assumptions only.

Assumptions:
- Zone RS-T (raffinate splitter). A hot-work permit (PW-TC-0098) is active for
  adjacent work; no shift-changeover signal is used here (unlike Vizag).
- LEL-RS (flammable gas, %LEL) drifts up from ~78 with late acceleration,
  breaching the 100 %LEL alarm at ~+38 min.
- CO-RS (a second gas) drifts slowly and crosses its alarm only near the end
  (so the naive multi-sensor AND-gate B2 has something, but late).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
T0 = datetime(2005, 3, 23, 12, 0, tzinfo=UTC)
BREACH = T0 + timedelta(minutes=38)
LEL_THRESHOLD = 100.0
CO_THRESHOLD = 50.0


def _iso(t: datetime) -> str:
    return t.isoformat()


def _lel(m: float) -> float:
    return round(78.0 + 0.5 * m + 0.05 * max(0.0, m - 28.0) ** 2, 2)


def _co(m: float) -> float:
    return round(30.0 + 0.55 * m, 2)


def build_events() -> list[dict]:
    events: list[dict] = [{
        "type": "permit", "ts": _iso(T0 + timedelta(minutes=10)),
        "permitId": "PW-TC-0098", "kind": "hot-work", "zoneId": "RS-T",
        "equipmentId": "blowdown-stack",
        "validFrom": _iso(T0 + timedelta(minutes=10)),
        "validTo": _iso(BREACH + timedelta(minutes=30)),
    }]
    t, end = T0, BREACH + timedelta(minutes=5)
    while t <= end:
        m = (t - T0).total_seconds() / 60.0
        events.append({"type": "reading", "ts": _iso(t), "sensorId": "LEL-RS",
                       "kind": "gas-lel", "unit": "%LEL", "zoneId": "RS-T", "value": _lel(m)})
        events.append({"type": "reading", "ts": _iso(t), "sensorId": "CO-RS",
                       "kind": "gas-co", "unit": "ppm", "zoneId": "RS-T", "value": _co(m)})
        t += timedelta(seconds=30)
    return events


def build_ground_truth() -> dict:
    return {
        "incidentId": "bp-texas-city-2005",
        "title": "BP Texas City raffinate splitter explosion (reconstructed)",
        "zoneId": "RS-T",
        "breachTs": _iso(BREACH),
        "thresholdSensor": "LEL-RS",
        "thresholds": {"gas-lel": LEL_THRESHOLD, "gas-co": CO_THRESHOLD},
        "expectedConvergence": ["hot-work permit", "rising flammable gas"],
        "source": "CSB final report (synthesis, not extraction)",
    }


def build_feedback() -> list[dict]:
    base = {"actor": "operator", "timestamp": _iso(BREACH)}
    return [
        {**base, "findingId": "seed-1", "verdict": "useful"},
        {**base, "findingId": "seed-2", "verdict": "useful"},
        {**base, "findingId": "seed-3", "verdict": "useful"},
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
