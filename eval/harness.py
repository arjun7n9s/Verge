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

from verge_schema.core import Permit, Reading, Sensor

from eval.baselines import (
    b0_fixed_threshold,
    b1_rate_of_rise,
    b2_multi_sensor_and_gate,
)
from eval.runtime import (
    REPLAYS,
    band_calibrated,
    compound_catch_stats,
    load_replay,
    run_verge_stream,
)

OUT = Path(__file__).parent / "out"


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _load_legacy(incident: str):
    """Load sensors/readings for baseline detectors (B0/B1/B2)."""
    _, events = load_replay(incident)
    gt = json.loads((REPLAYS / incident / "ground-truth.json").read_text(encoding="utf-8"))
    sensors: dict[str, Sensor] = {}
    readings: dict[str, list[Reading]] = {}
    permits: list[Permit] = []
    changeovers: list[tuple[datetime, datetime, str]] = []
    pending_start: dict[str, datetime] = {}

    for e in events:
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
    return gt, sensors, readings


def _lead_min(breach: datetime, alert: datetime | None) -> float | None:
    return None if alert is None else round((breach - alert).total_seconds() / 60.0, 1)


def _is_miss(lead_min: float | None) -> bool:
    """A method misses an incident if it never alerted, or alerted too late to
    matter (at/after the breach). This is the false-negative-rate primitive —
    the brief's own words: 'the metric that actually saves lives'."""
    return lead_min is None or lead_min <= 0


def run_incident(incident: str) -> dict:
    gt, events = load_replay(incident)
    gt_legacy, sensors, readings = _load_legacy(incident)
    assert gt_legacy["incidentId"] == gt["incidentId"]

    breach = _dt(gt["breachTs"])
    thresholds = gt["thresholds"]
    cfg = gt.get("config", {})
    window = cfg.get("windowReadings", 12)

    verge_ts, verge_band = run_verge_stream(gt, events, window=window)
    lead = _lead_min(breach, verge_ts)

    b0 = b0_fixed_threshold(readings, sensors, thresholds)
    b1 = b1_rate_of_rise(readings, sensors, thresholds,
                         rate_per_min=cfg.get("b1RatePerMin", 2.0))
    b2 = b2_multi_sensor_and_gate(readings, sensors, thresholds,
                                  n_required=cfg.get("b2NRequired", 2),
                                  window_min=cfg.get("b2WindowMin", 5.0))

    fpr = None
    fpath = REPLAYS / incident / "feedback.jsonl"
    if fpath.exists():
        rows = [json.loads(x) for x in fpath.read_text(encoding="utf-8").splitlines() if x.strip()]
        if rows:
            fa = sum(1 for r in rows if r.get("verdict") == "false-alarm")
            fpr = round(fa / len(rows), 3)

    b0_lead = _lead_min(breach, b0)
    b1_lead = _lead_min(breach, b1)
    b2_lead = _lead_min(breach, b2)
    compound = compound_catch_stats(gt, events, window=window)

    return {
        "incident": incident,
        "breachTs": gt["breachTs"],
        "compound": compound,
        "verge": {
            "alertTs": verge_ts.isoformat() if verge_ts else None,
            "band": verge_band,
            "leadMin": lead,
            "bandCalibrated": band_calibrated(verge_band, lead),
            "miss": _is_miss(lead),
        },
        "b0": {
            "alertTs": b0.isoformat() if b0 else None,
            "leadMin": b0_lead,
            "miss": _is_miss(b0_lead),
        },
        "b1": {
            "alertTs": b1.isoformat() if b1 else None,
            "leadMin": b1_lead,
            "miss": _is_miss(b1_lead),
        },
        "b2": {
            "alertTs": b2.isoformat() if b2 else None,
            "leadMin": b2_lead,
            "miss": _is_miss(b2_lead),
        },
        "fpr": fpr,
    }


def aggregate_fnr(results: list[dict]) -> dict:
    """False-negative rate per method across every replayed incident: the share
    of real incidents each method failed to flag before (or at/after) breach."""
    total = len(results)
    methods = ("verge", "b0", "b1", "b2")
    agg: dict[str, dict] = {}
    for m in methods:
        misses = sum(1 for r in results if r[m]["miss"])
        agg[m] = {
            "misses": misses,
            "total": total,
            "fnr": round(misses / total, 3) if total else None,
        }
    return agg


def aggregate_compound(results: list[dict]) -> dict:
    """Compound-only catch rate: multi-kind lineage findings / all Verge findings."""
    findings = sum(int(r.get("compound", {}).get("findings") or 0) for r in results)
    compound = sum(int(r.get("compound", {}).get("compound") or 0) for r in results)
    return {
        "findings": findings,
        "compound": compound,
        "catchRate": round(compound / findings, 3) if findings else None,
    }


def _fmt(v) -> str:
    return "silent" if v is None else str(v)


def _lead(v) -> str:
    return "silent" if v is None else f"{v} min"


_METHOD_LABEL = {
    "verge": "Verge",
    "b0": "B0 fixed threshold",
    "b1": "B1 rate-of-rise",
    "b2": "B2 AND-gate (multi-sensor)",
}


def render_markdown(results: list[dict]) -> str:
    lines = [
        "# Verge replay report",
        "",
        "> Reconstructions, not ground truth (spec §10). A regression test and a",
        "> demo — the first unbiased number comes from a pilot's own history.",
        "",
        "| Incident | Verge lead (band) | Band OK | B0 fixed | B1 rate | B2 AND-gate | FPR |",
        "|----------|-------------------|---------|----------|---------|-------------|-----|",
    ]
    for r in results:
        v = r["verge"]
        verge = f"{_lead(v['leadMin'])} ({_fmt(v['band'])})"
        cal = v.get("bandCalibrated")
        cal_s = "—" if cal is None else ("yes" if cal else "no")
        lines.append(
            f"| {r['incident']} | **{verge}** | {cal_s} | {_lead(r['b0']['leadMin'])} "
            f"| {_lead(r['b1']['leadMin'])} | {_lead(r['b2']['leadMin'])} "
            f"| {_fmt(r['fpr'])} |"
        )
    lines += [
        "",
        "_Lead = minutes between first alert and threshold breach. "
        "Band OK = alert band matched minutes-to-breach. "
        "Higher lead is better; 'silent' = never alerted before breach._",
        "",
        "## False-negative rate — the metric that actually saves lives",
        "",
        "> A **miss** is any incident a method never flagged before breach (silent, or",
        "> alerted at/after the fact). FNR = misses / incidents replayed. This is the",
        "> same lead-time data above, stated the way it matters operationally: how many",
        "> of these real incidents would each method have let through.",
        "",
        "| Method | Misses | Incidents | FNR |",
        "|--------|--------|-----------|-----|",
    ]
    agg = aggregate_fnr(results)
    for m in ("verge", "b0", "b1", "b2"):
        a = agg[m]
        pct = "—" if a["fnr"] is None else f"{a['fnr'] * 100:.0f}%"
        lines.append(f"| {_METHOD_LABEL[m]} | {a['misses']} | {a['total']} | **{pct}** |")
    compound = aggregate_compound(results)
    rate = compound["catchRate"]
    rate_s = "—" if rate is None else f"{rate * 100:.0f}%"
    lines += [
        "",
        "## Compound-only catch rate (Phase 2)",
        "",
        "Share of Verge findings whose contributing signals span ≥2 kinds "
        "(sensor/permit/voice/vision/…).",
        "",
        "| Compound findings | Total findings | Catch rate |",
        "|-------------------|----------------|------------|",
        f"| {compound['compound']} | {compound['findings']} | **{rate_s}** |",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verge replay harness")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--incident", help="replay id (default: --all)")
    grp.add_argument("--all", action="store_true", help="run every replay under eval/replays/")
    args = ap.parse_args()

    if args.incident:
        incidents = [args.incident]
    else:
        incidents = sorted(p.name for p in REPLAYS.iterdir()
                           if (p / "ground-truth.json").exists())

    results = [run_incident(i) for i in incidents]
    OUT.mkdir(exist_ok=True)
    # report.json stays a bare array (existing contract: GET /eval/report,
    # EvalReportPanel.tsx) — each incident dict gained a "miss" flag per method,
    # additive only. The FNR rollup lives in its own file + its own route.
    report_json = json.dumps(results, indent=2, default=str) + "\n"
    (OUT / "report.json").write_text(report_json, encoding="utf-8")
    aggregate_json = json.dumps(aggregate_fnr(results), indent=2) + "\n"
    (OUT / "aggregate.json").write_text(aggregate_json, encoding="utf-8")
    md = render_markdown(results)
    (OUT / "report.md").write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
