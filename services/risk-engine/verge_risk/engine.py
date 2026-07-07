"""The Compound Risk Engine (spec §4.1). LLM-independent (P1).

Evaluates the Safety Rules DSL over each zone of a RiskContext snapshot, fuses
the lead-time forecaster, applies sensor-health down-weighting, and emits
RiskFindings with full source lineage.
"""

from __future__ import annotations

import os

from verge_forecaster import forecast
from verge_schema.core import Reading
from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding

from .context import RiskContext, ZoneView
from .health import classify, is_degraded
from .rules import SEVERITY_CONFIDENCE, Rule


def _slope_per_min(readings: list[Reading]) -> float:
    if len(readings) < 2:
        return 0.0
    t0 = readings[0].ts
    xs = [(r.ts - t0).total_seconds() for r in readings]
    ys = [r.value for r in readings]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx) * 60.0


# ── predicate implementations ────────────────────────────────────────────────
# Each returns a ContributingSignal when matched, else None.


def _p_permit_active(zv: ZoneView, params: dict) -> ContributingSignal | None:
    permits = zv.active_permits(kind=params.get("kind"))
    if not permits:
        return None
    p = permits[0]
    return ContributingSignal(
        kind="permit", ref_id=p.permit_id, summary=f"{p.kind} permit active", ts=zv.ctx.now
    )


def _p_shift_changeover(zv: ZoneView, params: dict) -> ContributingSignal | None:
    if not zv.ctx.in_changeover:
        return None
    return ContributingSignal(kind="shift", ref_id="changeover", summary="shift changeover window")


def _p_gas_near_threshold(zv: ZoneView, params: dict) -> ContributingSignal | None:
    """Match if a gas sensor is within `pct` below its alarm threshold OR rising."""
    kind = params["sensor_kind"]
    pct = float(params.get("pct", 0.10))
    min_rise = float(params.get("min_rise_per_min", 0.0))
    threshold = zv.ctx.thresholds.get(kind)
    for s in zv.sensors_of_kind(kind):
        reads = zv.readings_for(s.sensor_id)
        if not reads:
            continue
        value = reads[-1].value
        rising = _slope_per_min(reads) > max(min_rise, 0.0)
        near = threshold is not None and value >= (1.0 - pct) * threshold
        if near or rising:
            why = "near threshold" if near else "rising"
            return ContributingSignal(
                kind="reading",
                ref_id=s.sensor_id,
                summary=f"{kind} {value:.1f} ({why})",
                ts=reads[-1].ts,
            )
    return None


PREDICATES = {
    "permit_active": _p_permit_active,
    "shift_changeover": _p_shift_changeover,
    "gas_near_threshold": _p_gas_near_threshold,
}


def _zone_ids(ctx: RiskContext) -> list[str]:
    return sorted({s.zone_id for s in ctx.sensors.values()})


def _graph_incomplete(zone_id: str) -> bool:
    if os.environ.get("VERGE_NEO4J_GRAPH_QUERY", "").lower() not in ("1", "true", "yes"):
        return False
    from verge_twin.neo4j_query import zone_graph_coverage

    cov = zone_graph_coverage(zone_id)
    return bool(cov.get("degraded") or cov.get("coveragePct", 100) < 80)


def _degraded_sensors(zv: ZoneView, signals: list[ContributingSignal]) -> list[str]:
    bad: list[str] = []
    for sig in signals:
        if sig.kind != "reading":
            continue
        s = zv.ctx.sensors.get(sig.ref_id)
        if s is None:
            continue
        q = classify(s, zv.readings_for(s.sensor_id), now=zv.ctx.now)
        if is_degraded(q):
            bad.append(s.sensor_id)
    return bad


def evaluate(ctx: RiskContext, rules: list[Rule]) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    seq = 0
    for zone_id in _zone_ids(ctx):
        zv = ctx.zone(zone_id)
        for rule in rules:
            signals: list[ContributingSignal] = []
            matched = True
            for pred in rule.predicates:
                fn = PREDICATES.get(pred["type"])
                if fn is None:
                    matched = False
                    break
                sig = fn(zv, pred)
                if sig is None:
                    matched = False
                    break
                signals.append(sig)
            if not matched:
                continue

            degraded_by = _degraded_sensors(zv, signals)
            degraded = bool(degraded_by)

            band, basis, quality = LeadTimeBand.UNKNOWN, None, EstimateQuality.LOW
            if rule.forecast:
                fc = _run_forecast(zv, rule.forecast.sensor_kind, degraded)
                if fc:
                    band, basis, quality = fc

            confidence = SEVERITY_CONFIDENCE.get(rule.severity, rule.base_confidence)
            if degraded:
                confidence *= 0.7  # down-weight findings resting on bad data (§4.7)

            seq += 1
            graph_incomplete = _graph_incomplete(zone_id)
            findings.append(
                RiskFinding(
                    finding_id=f"F-{ctx.now:%Y%m%dT%H%M%S}-{seq:03d}",
                    created_at=ctx.now,
                    zone_id=zone_id,
                    title=rule.name,
                    state=FindingState.NEW,
                    confidence=round(confidence, 3),
                    contributing_signals=signals,
                    lead_time_band=band,
                    lead_time_basis=basis,
                    estimate_quality=quality,
                    confidence_degraded=degraded,
                    confidence_degraded_by=degraded_by,
                    counterfactual=_counterfactual(signals),
                    lineage=[f"{s.kind}:{s.ref_id}" for s in signals],
                    graph_incomplete=graph_incomplete,
                )
            )
    return findings


def _run_forecast(zv: ZoneView, sensor_kind: str, degraded: bool):
    threshold = zv.ctx.thresholds.get(sensor_kind)
    for s in zv.sensors_of_kind(sensor_kind):
        reads = zv.readings_for(s.sensor_id)
        if not reads or threshold is None:
            continue
        t0 = reads[0].ts
        samples = [((r.ts - t0).total_seconds(), r.value) for r in reads]
        f = forecast(samples, threshold, degraded=degraded)
        return f.band, f.basis, f.quality
    return None


def _counterfactual(signals: list[ContributingSignal]) -> str | None:
    permit = next((s for s in signals if s.kind == "permit"), None)
    if permit:
        return f"risk drops to LOW if permit {permit.ref_id} is closed"
    return None
