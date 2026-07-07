"""Model registry lifecycle + PSI drift detection (spec §14 Phase 4)."""

from __future__ import annotations

import random

import pytest
from verge_mlops import (
    PRODUCTION,
    SHADOW,
    DriftResult,
    IllegalPromotion,
    ModelCard,
    ModelRegistry,
    population_stability_index,
)


def _card(model_id: str, version: str, name: str = "compound-risk") -> ModelCard:
    return ModelCard(model_id=model_id, name=name, version=version, kind="isolation-forest")


# ── registry lifecycle ──────────────────────────────────────────────────────


def test_promotion_follows_the_lifecycle():
    reg = ModelRegistry()
    reg.register(_card("m1", "1.0.0"))
    reg.promote("m1", SHADOW)
    reg.promote("m1", "canary")
    reg.promote("m1", PRODUCTION)
    assert reg.production("compound-risk").model_id == "m1"


def test_illegal_promotion_rejected():
    reg = ModelRegistry()
    reg.register(_card("m1", "1.0.0"))
    with pytest.raises(IllegalPromotion):
        reg.promote("m1", PRODUCTION)  # cannot jump registered -> production


def test_promoting_replacement_retires_incumbent():
    reg = ModelRegistry()
    for mid, ver in [("m1", "1.0.0"), ("m2", "2.0.0")]:
        reg.register(_card(mid, ver))
        reg.promote(mid, SHADOW)
        reg.promote(mid, "canary")
    reg.promote("m1", PRODUCTION)
    reg.promote("m2", PRODUCTION)
    assert reg.production("compound-risk").model_id == "m2"
    assert reg.get("m1").stage == "retired"
    # Exactly one production model per name.
    assert len(reg.list(stage=PRODUCTION)) == 1


def test_registry_persists_to_disk(tmp_path):
    path = tmp_path / "registry.json"
    reg = ModelRegistry(path)
    reg.register(_card("m1", "1.0.0"))
    reg.promote("m1", SHADOW)
    reloaded = ModelRegistry(path)
    assert reloaded.get("m1").stage == SHADOW
    assert reloaded.summary()["total"] == 1


# ── drift ────────────────────────────────────────────────────────────────────


def test_identical_distributions_are_stable():
    ref = [float(i % 20) for i in range(400)]
    result = population_stability_index(ref, list(ref))
    assert result.severity == "stable"
    assert not result.drifted


def test_shifted_distribution_flags_significant_drift():
    rng = random.Random(42)
    ref = [rng.gauss(0, 1) for _ in range(1000)]
    shifted = [rng.gauss(3, 1) for _ in range(1000)]  # mean shifted by 3 sigma
    result = population_stability_index(ref, shifted)
    assert result.severity == "significant"
    assert result.drifted
    assert result.psi > 0.25


def test_empty_inputs_degrade_to_stable():
    assert population_stability_index([], [1.0, 2.0]).severity == "stable"


def test_drift_result_serializes():
    d = DriftResult(psi=0.3, severity="significant", bins=10, n_reference=100, n_current=100)
    assert d.to_dict()["drifted"] is True


def test_nan_in_reference_does_not_yield_false_stable():
    # A drift monitor must not silently report "stable" on garbage input.
    rng = random.Random(7)
    ref = [rng.gauss(0, 1) for _ in range(500)] + [float("nan"), float("inf")]
    shifted = [rng.gauss(3, 1) for _ in range(500)]
    result = population_stability_index(ref, shifted)
    assert result.severity == "significant"  # non-finite dropped, real drift seen


def test_registry_ignores_unknown_fields_on_load(tmp_path):
    import json

    path = tmp_path / "reg.json"
    # A registry written by a newer version with an extra field must still load.
    path.write_text(json.dumps({"models": [{
        "model_id": "m1", "name": "cr", "version": "1.0.0", "kind": "isolation-forest",
        "stage": "production", "future_field": {"unknown": True},
    }]}), encoding="utf-8")
    reg = ModelRegistry(path)
    assert reg.get("m1").stage == "production"
