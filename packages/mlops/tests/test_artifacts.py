"""Registry artifact loading tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from verge_mlops.artifacts import (
    ArtifactError,
    artifact_root,
    load_sklearn_bundle,
    production_model,
    sha256_file,
)
from verge_mlops.registry import DEMO_REGISTRY, ModelCard, ModelRegistry


def test_production_model_from_demo_registry() -> None:
    card = production_model("compound-risk")
    assert card is not None
    assert card.version == "1.2.0"
    assert card.artifact_ref == "compound-risk-1.2.0.pkl"


def test_load_sklearn_bundle_with_digest() -> None:
    reg = ModelRegistry.read_only(DEMO_REGISTRY)
    card = reg.production("compound-risk")
    assert card is not None
    root = artifact_root(DEMO_REGISTRY)
    bundle = load_sklearn_bundle(card, root=root)
    assert bundle["feature_dim"] == 5
    assert hasattr(bundle["model"], "decision_function")


def test_digest_mismatch_rejected(tmp_path: Path) -> None:
    reg = ModelRegistry.read_only(DEMO_REGISTRY)
    card = reg.production("compound-risk")
    assert card is not None
    bad = ModelCard.from_raw({**card.to_dict(), "artifact_digest": "0" * 64})
    root = artifact_root(DEMO_REGISTRY)
    with pytest.raises(ArtifactError):
        load_sklearn_bundle(bad, root=root)


def test_sha256_matches_registry() -> None:
    reg = ModelRegistry.read_only(DEMO_REGISTRY)
    card = reg.production("compound-risk")
    assert card is not None
    path = artifact_root(DEMO_REGISTRY) / card.artifact_ref
    assert sha256_file(path) == card.artifact_digest
