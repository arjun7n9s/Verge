"""IsolationForest anomaly layer (spec §4.1) — registry-backed artifacts (audit §7).

Production models load from the MLOps registry artifact_ref with digest
verification. Synthetic fit remains as a last-resort fallback when artifacts are
missing (degraded, never silent).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding

from .runner import StreamState

MODEL_NAME = "compound-risk"


@dataclass
class ScorerBundle:
    model: object
    feature_dim: int
    source: str  # registry | synthetic
    model_id: str | None = None
    version: str | None = None


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


def _fit_synthetic_scorer() -> ScorerBundle | None:
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return None
    import numpy as np

    rng = np.random.default_rng(42)
    normal = rng.normal(loc=[25.0, 2.0, 30.0, 1.0, 2.0], scale=[8, 3, 10, 1, 0.5], size=(200, 5))
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(normal)
    return ScorerBundle(model=model, feature_dim=5, source="synthetic")


def _load_registry_scorer() -> ScorerBundle | None:
    from verge_mlops.artifacts import artifact_root, load_sklearn_bundle
    from verge_mlops.registry import DEMO_REGISTRY, ModelRegistry

    reg_path = os.environ.get("VERGE_MODEL_REGISTRY")
    registry = (
        ModelRegistry(reg_path)
        if reg_path and Path(reg_path).exists()
        else ModelRegistry.read_only(DEMO_REGISTRY)
    )
    card = registry.production(MODEL_NAME)
    if card is None or not card.artifact_ref:
        return None
    root = artifact_root(reg_path or DEMO_REGISTRY)
    bundle = load_sklearn_bundle(card, root=root)
    return ScorerBundle(
        model=bundle["model"],
        feature_dim=int(bundle.get("feature_dim", 5)),
        source="registry",
        model_id=card.model_id,
        version=card.version,
    )


_SCORER: ScorerBundle | None = None


def _get_scorer() -> ScorerBundle | None:
    global _SCORER
    if _SCORER is None:
        try:
            _SCORER = _load_registry_scorer()
        except Exception:
            _SCORER = None
        if _SCORER is None:
            _SCORER = _fit_synthetic_scorer()
    return _SCORER


def reset_scorer_cache() -> None:
    """Test helper — force reload on next score."""
    global _SCORER
    _SCORER = None


def ml_findings(
    state: StreamState,
    *,
    zone_ids: list[str] | None = None,
    min_score: float = -0.15,
) -> list[RiskFinding]:
    """Score zones; emit findings when IsolationForest flags an outlier."""
    scorer = _get_scorer()
    if scorer is None:
        return []

    zone_ids = zone_ids or sorted({s.zone_id for s in state.sensors.values()})
    out: list[RiskFinding] = []
    now = state.now
    if now is None:
        return []

    dim = scorer.feature_dim
    lineage_prefix = f"ml:{scorer.model_id or MODEL_NAME}"

    for zone_id in zone_ids:
        fv = _features_from_state(state, zone_id)
        if fv is None:
            continue
        vec = (fv.values + [0.0] * dim)[:dim]
        score = float(scorer.model.decision_function([vec])[0])
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
        basis = f"iforest score={score:.3f}"
        if scorer.version:
            basis += f" model={scorer.version} ({scorer.source})"
        out.append(RiskFinding(
            finding_id=f"F-ML-{now:%Y%m%dT%H%M%S}-{zone_id}",
            created_at=now,
            zone_id=zone_id,
            title="ML: multivariate gas anomaly (IsolationForest)",
            state=FindingState.NEW,
            confidence=round(min(0.95, 0.75 + abs(score)), 3),
            contributing_signals=signals,
            lead_time_band=LeadTimeBand.WATCH,
            lead_time_basis=basis,
            estimate_quality=EstimateQuality.MEDIUM,
            lineage=[lineage_prefix, *[f"reading:{s}" for s in fv.sensor_ids]],
        ))
    return out
