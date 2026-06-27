"""Replay harness: run Verge + baselines B0/B1/B2 over a reconstructed incident
and report lead time, band, and FPR (spec §10).

    python -m eval.harness --all
    python -m eval.harness --incident vizag-2025-01
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from . import _paths  # noqa: F401  (sys.path bootstrap; must precede verge imports)

from verge_risk import STARTER_RULES, evaluate, load_rules  # noqa: E402
from verge_risk.context import RiskContext  # noqa: E402
from verge_schema.core import Permit, Reading, Sensor  # noqa: E402

from eval.baselines import (  # noqa: E402
    b0_fixed_threshold,
    b1_rate_of_rise,
    b2_multi_sensor_and_gate,
)

REPLAYS = Path(__file__).parent / "replays"
OUT = Path(__file__).parent / "out"
WINDOW = 12  # readings carried into each RiskContext tick (~6 min at 30s cadence)


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _load(incident: str):
    d = REPLAYS / incident
    gt = json.loads((d / "ground-truth.json").read_text(encoding="utf-8"))
    sensors: dict[str, Sensor] = {}
    readings: dict[str, list[Reading]] = {}
    permits: list[Permit] = []
    changeovers: list[tuple[datetime, datetime, str]] = []
    pending_start: dict[str, datetime] = {}

    for line in (d / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e["type"] == "reading":
            sid = e["sensorId"]
            if sid not in sensors:
                sensors[sid] = Sensor(
                    sensor_id=sid, kind=e["kind"], unit=e["unit"], zone_id=e["zoneId"],
                    expected_cadence_s=30.0, plausible_min=0.0, plausible_max=1e6,
                )
            readings.setdefault(sid, []).append(
                Reading(sensor_id=sid, ts=_dt(e["ts"]), value=e["value"])
            )
        elif e["type"] == "permit":
            permits.append(Permit(
                permit_id=e["permitId"], kind=e["kind"], zone_id=e["zoneId"],
                equipment_id=e.get("equipmentId"),
                valid_from=_dt(e["validFrom"]), valid_to=_dt(e["validTo"]),
            ))
        elif e["type"] == "shift":
            if e["event"] == "changeover-start":
                pending_start[e["zoneId"]] = _dt(e["ts"])
            elif e["event"] == "changeover-end" and e["zoneId"] in pending_start:
                changeovers.append((pending_start.pop(e["zoneId"]), _dt(e["ts"]), e["zoneId"]))

    for r in readings.values():
        r.sort(key=lambda x: x.ts)
    return gt, sensors, readings, permits, changeovers


def _in_changeover(t: datetime, changeovers, zone: str) -> bool:
    return any(s <= t <= e and z == zone for s, e, z in changeovers)


def run_verge(gt, sensors, readings, permits, changeovers):
    """Tick through the timeline; return (first_alert_ts, band) for the target zone."""
    rules = load_rules(STARTER_RULES)
    thresholds = gt["thresholds"]
    zone = gt["zoneId"]
    ticks = sorted({r.ts for reads in readings.values() for r in reads})

    for tick in ticks:
        windowed = {
            sid: [r for r in reads if r.ts <= tick][-WINDOW:] for sid, reads in readings.items()
        }
        windowed = {sid: w for sid, w in windowed.items() if w}
        ctx = RiskContext(
            now=tick, sensors=sensors, readings=windowed, permits=permits,
            thresholds=thresholds, in_changeover=_in_changeover(tick, changeovers, zone),
        )
        findings = evaluate(ctx, rules)
        crit = [f for f in findings if f.zone_id == zone and f.confidence >= 0.8]
        if crit:
            return tick, crit[0].lead_time_band
    return None, None


def _lead_min(breach: datetime, alert: datetime | None) -> float | None:
    return None if alert is None else round((breach - alert).total_seconds() / 60.0, 1)


def run_incident(incident: str) -> dict:
    gt, sensors, readings, permits, changeovers = _load(incident)
    breach = _dt(gt["breachTs"])
    thresholds = gt["thresholds"]

    verge_ts, verge_band = run_verge(gt, sensors, readings, permits, changeovers)
    b0 = b0_fixed_threshold(readings, sensors, thresholds)
    b1 = b1_rate_of_rise(readings, sensors, thresholds)
    b2 = b2_multi_sensor_and_gate(readings, sensors, thresholds)

    # FPR from synthetic feedback (real feedback replaces this in Horizon 1)
    fpr = None
    fpath = REPLAYS / incident / "feedback.jsonl"
    if fpath.exists():
        rows = [json.loads(x) for x in fpath.read_text(encoding="utf-8").splitlines() if x.strip()]
        if rows:
            fa = sum(1 for r in rows if r.get("verdict") == "false-alarm")
            fpr = round(fa / len(rows), 3)

    return {
        "incident": incident,
        "breachTs": gt["breachTs"],
        "verge": {"alertTs": verge_ts.isoformat() if verge_ts else None,
                  "band": verge_band, "leadMin": _lead_min(breach, verge_ts)},
        "b0": {"alertTs": b0.isoformat() if b0 else None, "leadMin": _lead_min(breach, b0)},
        "b1": {"alertTs": b1.isoformat() if b1 else None, "leadMin": _lead_min(breach, b1)},
        "b2": {"alertTs": b2.isoformat() if b2 else None, "leadMin": _lead_min(breach, b2)},
        "fpr": fpr,
    }


def _fmt(v) -> str:
    return "silent" if v is None else str(v)


def _lead(v) -> str:
    return "silent" if v is None else f"{v} min"


def render_markdown(results: list[dict]) -> str:
    lines = [
        "# Verge replay report",
        "",
        "> Reconstructions, not ground truth (spec §10). A regression test and a",
        "> demo — the first unbiased number comes from a pilot's own history.",
        "",
        "| Incident | Verge lead (band) | B0 fixed | B1 rate | B2 AND-gate | FPR |",
        "|----------|-------------------|----------|---------|-------------|-----|",
    ]
    for r in results:
        v = r["verge"]
        verge = f"{_lead(v['leadMin'])} ({_fmt(v['band'])})"
        lines.append(
            f"| {r['incident']} | **{verge}** | {_lead(r['b0']['leadMin'])} "
            f"| {_lead(r['b1']['leadMin'])} | {_lead(r['b2']['leadMin'])} "
            f"| {_fmt(r['fpr'])} |"
        )
    lines += ["", "_Lead = minutes between first alert and threshold breach. "
              "Higher is better; 'silent' = never alerted before breach._", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verge replay harness")
    ap.add_argument("--incident", help="replay id (default: --all)")
    ap.add_argument("--all", action="store_true", help="run every replay under eval/replays/")
    args = ap.parse_args()

    if args.incident:
        incidents = [args.incident]
    else:
        incidents = sorted(p.name for p in REPLAYS.iterdir()
                           if (p / "ground-truth.json").exists())

    results = [run_incident(i) for i in incidents]
    OUT.mkdir(exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    md = render_markdown(results)
    (OUT / "report.md").write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
