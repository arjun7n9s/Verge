"""Shared replay runtime — same path as `python -m verge_risk` (spec §10).

Loads canonical JSONL replays and drives `run_stream` with optional SIMOPS +
plant adjacency, so the eval harness and the live CLI share one code path.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from verge_permit import conflict_findings
from verge_risk import STARTER_RULES, load_rules, run_stream
from verge_schema.enums import BAND_BOUNDS_MIN, LeadTimeBand
from verge_twin import load_plant

REPLAYS = Path(__file__).resolve().parent / "replays"
DEFAULT_WINDOW = 12


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def load_replay(incident: str) -> tuple[dict, list[dict]]:
    """Return (ground-truth, events) for a replay id under eval/replays/."""
    d = REPLAYS / incident
    gt = json.loads((d / "ground-truth.json").read_text(encoding="utf-8"))
    events: list[dict] = []
    for line in (d / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    events.sort(key=lambda e: e["ts"])
    return gt, events


def simops_detector(adjacency: dict[str, set[str]]):
    """SIMOPS detector closure — same wiring as verge_risk.__main__."""

    def detect(state):
        return conflict_findings(
            state.permits, adjacency=adjacency, now=state.now, at=state.now
        )

    return detect


def resolve_runtime(gt: dict) -> tuple[dict[str, float], dict[str, set[str]], bool]:
    """Thresholds, zone adjacency, and whether SIMOPS is enabled for this replay."""
    cfg = gt.get("config", {})
    thresholds = dict(gt["thresholds"])
    adjacency: dict[str, set[str]] = {}
    simops = cfg.get("simops", False)

    plant_path = cfg.get("plantModel") or gt.get("plantModel")
    if plant_path:
        plant = load_plant(plant_path)
        thresholds = {**plant.thresholds_by_kind(), **thresholds}
        adjacency = plant.adjacency()
        simops = True
    elif simops:
        adjacency = {gt["zoneId"]: set()}

    return thresholds, adjacency, simops


def run_verge_stream(
    gt: dict,
    events: list[dict],
    *,
    window: int = DEFAULT_WINDOW,
) -> tuple[datetime | None, LeadTimeBand | None]:
    """Run the unified runtime; return (first_alert_ts, band) for the target zone.

    Lead-time metric uses gas-rule findings (forecast bands), not SIMOPS-only
    alerts (UNKNOWN band).
    """
    rules = load_rules(STARTER_RULES)
    thresholds, adjacency, simops = resolve_runtime(gt)
    zone = gt["zoneId"]
    collected: list = []

    detectors = [simops_detector(adjacency)] if simops else []
    run_stream(
        events,
        rules,
        collected.append,
        thresholds=thresholds,
        detectors=detectors,
        window=window,
        min_confidence=0.8,
        zone_adjacency=adjacency,
    )

    gas_bands = {LeadTimeBand.IMMINENT, LeadTimeBand.NEAR, LeadTimeBand.WATCH}
    for f in sorted(collected, key=lambda x: x.created_at):
        if f.zone_id != zone or f.confidence < 0.8:
            continue
        if f.title.startswith("SIMOPS"):
            continue
        if f.lead_time_band in gas_bands:
            return f.created_at, f.lead_time_band
    return None, None


def band_calibrated(band: LeadTimeBand | None, lead_min: float | None) -> bool | None:
    """Did the alert band match actual minutes-to-breach? None if not applicable."""
    if band is None or lead_min is None or band is LeadTimeBand.UNKNOWN:
        return None
    lo, hi = BAND_BOUNDS_MIN[band]
    if lo is not None and lead_min < lo:
        return False
    return not (hi is not None and lead_min >= hi)


def compound_catch_stats(
    gt: dict,
    events: list[dict],
    *,
    window: int = DEFAULT_WINDOW,
) -> dict:
    """Share of Verge findings whose lineage spans ≥2 signal kinds (Phase 2)."""
    rules = load_rules(STARTER_RULES)
    thresholds, adjacency, simops = resolve_runtime(gt)
    collected: list = []
    detectors = [simops_detector(adjacency)] if simops else []
    run_stream(
        events,
        rules,
        collected.append,
        thresholds=thresholds,
        detectors=detectors,
        window=window,
        min_confidence=0.8,
        zone_adjacency=adjacency,
    )
    zone = gt["zoneId"]
    zone_findings = [f for f in collected if f.zone_id == zone and f.confidence >= 0.8]
    compound = [
        f
        for f in zone_findings
        if len({s.kind for s in f.contributing_signals}) >= 2
    ]
    total = len(zone_findings)
    return {
        "findings": total,
        "compound": len(compound),
        "catchRate": round(len(compound) / total, 3) if total else None,
    }
