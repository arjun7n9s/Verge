"""IsolationForest anomaly layer (spec §4.1) — optional sklearn, rules fallback (P1).

Inspired by SPINE/HarmonicMesh: multivariate sensor features scored in shadow/canary
via the MLOps router before promotion to production findings.
"""

from __future__ import annotations

from dataclasses import dataclass

from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding

from .runner import StreamState

MODEL_NAME = "isolation-forest-gas"


@dataclass
class FeatureVector:
    zone_id: str
    values: list[float]
    sensor_ids: list[str]


def _features_from_state(state: StreamState, zone_id: str) -> FeatureVector | None:
    """Build a multivariate vector: mean LEL, max LEL, slope, sensor count."""
    vals: list[float] = []
    sids: list[str] = []
    for sid, dq in state.readings.items():
        sensor = state.sensors.get(sid)
        if sensor is None or sensor.zone_id != zone_id:
            continue
        if not str(sensor.kind).startswith("gas"):
            continue
        pts = list(dq)
        if not pts:
            continue
        vals.extend([pts[-1].value, (pts[-1].value - pts[0].value)])
        sids.append(sid)
    if len(vals) < 2:
        return None
    vals.append(float(len(sids)))
    return FeatureVector(zone_id=zone_id, values=vals, sensor_ids=sids)


def _fit_scorer():
    """Lazy singleton: fit on nominal plant operating envelope."""
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return None
    import numpy as np

    # Nominal coke-oven envelope (demo plant); replaced by pilot history in production.
    rng = np.random.default_rng(42)
    normal = rng.normal(loc=[25.0, 2.0, 30.0, 1.0, 2.0], scale=[8, 3, 10, 1, 0.5], size=(200, 5))
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(normal)
    return model


_SCORER = None


def _get_scorer():
    global _SCORER
    if _SCORER is None:
        _SCORER = _fit_scorer()
    return _SCORER


def ml_findings(
    state: StreamState,
    *,
    zone_ids: list[str] | None = None,
    min_score: float = -0.15,
) -> list[RiskFinding]:
    """Score zones; emit findings when IsolationForest flags an outlier."""
    model = _get_scorer()
    if model is None:
        return []


    zone_ids = zone_ids or sorted({s.zone_id for s in state.sensors.values()})
    out: list[RiskFinding] = []
    now = state.now
    if now is None:
        return []

    for zone_id in zone_ids:
        fv = _features_from_state(state, zone_id)
        if fv is None:
            continue
        # Pad/truncate to 5 features for the demo model.
        vec = (fv.values + [0.0] * 5)[:5]
        score = float(model.decision_function([vec])[0])
        if score >= min_score:
            continue
        signals = [
            ContributingSignal(
                kind="reading",
                ref_id=sid,
                summary="anomaly feature contributor",
                ts=now,
            )
            for sid in fv.sensor_ids[:3]
        ]
        out.append(RiskFinding(
            finding_id=f"F-ML-{now:%Y%m%dT%H%M%S}-{zone_id}",
            created_at=now,
            zone_id=zone_id,
            title="ML: multivariate gas anomaly (IsolationForest)",
            state=FindingState.NEW,
            confidence=round(min(0.95, 0.75 + abs(score)), 3),
            contributing_signals=signals,
            lead_time_band=LeadTimeBand.WATCH,
            lead_time_basis=f"iforest score={score:.3f}",
            estimate_quality=EstimateQuality.MEDIUM,
            lineage=[f"ml:{MODEL_NAME}", *[f"reading:{s}" for s in fv.sensor_ids]],
        ))
    return out
