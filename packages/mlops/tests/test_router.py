"""Model router: production default + canary-by-zone rollout (spec §14 P4)."""

from __future__ import annotations

from verge_mlops import (
    CANARY,
    PRODUCTION,
    SHADOW,
    ModelCard,
    ModelRegistry,
    ModelRouter,
)


def _registry() -> ModelRegistry:
    reg = ModelRegistry()
    reg.register(ModelCard("cr-1.2.0", "compound-risk", "1.2.0", "isolation-forest"))
    reg.promote("cr-1.2.0", SHADOW)
    reg.promote("cr-1.2.0", CANARY)
    reg.promote("cr-1.2.0", PRODUCTION)
    reg.register(ModelCard("cr-1.3.0", "compound-risk", "1.3.0", "isolation-forest"))
    reg.promote("cr-1.3.0", SHADOW)
    reg.promote("cr-1.3.0", CANARY)
    return reg


def test_defaults_to_production():
    router = ModelRouter(_registry())
    d = router.route("compound-risk")
    assert d.stage == PRODUCTION and d.model.version == "1.2.0"
    assert d.routed


def test_canary_zone_routes_to_canary():
    router = ModelRouter(_registry(), canary_zones={"compound-risk": {"B-04"}})
    d = router.route("compound-risk", zone="B-04")
    assert d.stage == CANARY and d.model.version == "1.3.0"
    # A non-canary zone still gets production.
    assert router.route("compound-risk", zone="B-01").stage == PRODUCTION


def test_unknown_model_is_degraded_route():
    d = ModelRouter(_registry()).route("nonexistent")
    assert not d.routed and d.model is None
    assert "no production or canary" in d.reason


def test_canary_only_model_falls_back_when_no_production():
    reg = ModelRegistry()
    reg.register(ModelCard("ppe-0.9", "ppe-detector", "0.9.0", "rt-detr"))
    reg.promote("ppe-0.9", SHADOW)
    reg.promote("ppe-0.9", CANARY)
    d = ModelRouter(reg).route("ppe-detector")
    assert d.stage == CANARY and "no production model" in d.reason
