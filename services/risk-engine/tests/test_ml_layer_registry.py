"""ML layer loads production artifact from registry."""

from __future__ import annotations

import pytest

pytest.importorskip("sklearn")

from verge_risk.ml_layer import _get_scorer, reset_scorer_cache


def test_scorer_loads_from_registry_artifact() -> None:
    reset_scorer_cache()
    scorer = _get_scorer()
    assert scorer is not None
    assert scorer.source == "registry"
    assert scorer.model_id == "compound-risk-1.2.0"
    assert scorer.feature_dim == 5
