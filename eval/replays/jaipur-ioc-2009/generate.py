"""Deterministic generator for the Jaipur IOC 2009 replay (spec §10.1).

RECONSTRUCTION, not ground truth (spec §10). The public inquiry describes a
gasoline release during a line-up operation at a tank farm, hot work nearby, and
a delayed evacuation. No per-sensor time-series exists; this is documented
synthesis — the SIMOPS archetype (hot work ∩ rising flammable gas).

Assumptions:
- Zone TF-A (tank farm). Hot-work permit (PW-JP-0451) active.
- LEL-TF drifts up from ~80 (~0.6 %LEL/min), breaching the 100 %LEL alarm at
  ~+33 min. Single gas sensor (so the multi-sensor AND-gate B2 stays silent).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
T0 = datetime(2009, 10, 29, 18, 0, tzinfo=UTC)
BREACH = T0 + timedelta(minutes=33)
LEL_THRESHOLD = 100.0


def _iso(t: datetime) -> str:
    return t.isoformat()


def _lel(m: float) -> float:
    return round(80.0 + 0.6 * m, 2)


def build_events() -> list[dict]:
    events: list[dict] = [{
        "type": "permit", "ts": _iso(T0 + timedelta(minutes=8)),
        "permitId": "PW-JP-0451", "kind": "hot-work", "zoneId": "TF-A",
        "equipmentId": "tank-401-manifold",
        "validFrom": _iso(T0 + timedelta(minutes=8)),
        "validTo": _iso(BREACH + timedelta(minutes=30)),
    }]
    t, end = T0, BREACH + timedelta(minutes=5)
    while t <= end:
        m = (t - T0).total_seconds() / 60.0
        events.append({"type": "reading", "ts": _iso(t), "sensorId": "LEL-TF",
                       "kind": "gas-lel", "unit": "%LEL", "zoneId": "TF-A", "value": _lel(m)})
        t += timedelta(seconds=30)
    return events


def build_ground_truth() -> dict:
    return {
        "incidentId": "jaipur-ioc-2009",
        "title": "Jaipur IOC tank-farm fire (reconstructed)",
        "zoneId": "TF-A",
        "breachTs": _iso(BREACH),
        "thresholdSensor": "LEL-TF",
        "thresholds": {"gas-lel": LEL_THRESHOLD},
        "expectedConvergence": ["hot-work permit", "rising flammable gas"],
        "source": "Public inquiry report (synthesis, not extraction)",
    }


def build_feedback() -> list[dict]:
    base = {"actor": "operator", "timestamp": _iso(BREACH)}
    return [
        {**base, "findingId": "seed-1", "verdict": "useful"},
        {**base, "findingId": "seed-2", "verdict": "useful"},
        {**base, "findingId": "seed-3", "verdict": "false-alarm", "reasonCode": "already-known"},
        {**base, "findingId": "seed-4", "verdict": "useful"},
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
