"""Load and verify model artifacts referenced by the registry (audit §7)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .registry import DEMO_REGISTRY, ModelCard, ModelRegistry

SAMPLES_DIR = Path(__file__).parent / "samples"
DEFAULT_ARTIFACT_ROOT = SAMPLES_DIR / "models"


class ArtifactError(ValueError):
    """Raised when an artifact is missing or fails digest verification."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_root(registry_path: Path | str | None = None) -> Path:
    env_root = os.environ.get("VERGE_ML_ARTIFACT_ROOT")
    if env_root:
        return Path(env_root)
    if registry_path:
        return Path(registry_path).resolve().parent / "models"
    return DEFAULT_ARTIFACT_ROOT


def resolve_artifact_path(card: ModelCard, *, root: Path | None = None) -> Path:
    if not card.artifact_ref:
        raise ArtifactError(f"model {card.model_id} has no artifact_ref")
    ref = Path(card.artifact_ref)
    if ref.is_absolute():
        path = ref
    else:
        base = root or artifact_root()
        path = base / ref
    if not path.exists():
        raise ArtifactError(f"artifact not found: {path}")
    return path


def verify_artifact(path: Path, expected_digest: str | None) -> None:
    if not expected_digest:
        return
    actual = sha256_file(path)
    if actual != expected_digest.lower():
        raise ArtifactError(f"digest mismatch for {path.name}")


def load_sklearn_bundle(
    card: ModelCard,
    *,
    root: Path | None = None,
) -> dict:
    """Load a joblib bundle ``{model, feature_dim, ...}`` for sklearn scorers."""
    path = resolve_artifact_path(card, root=root)
    verify_artifact(path, card.artifact_digest)
    try:
        import joblib
    except ImportError as exc:
        raise ArtifactError("joblib not installed") from exc
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise ArtifactError(f"invalid sklearn bundle at {path}")
    return bundle


def production_model(
    name: str,
    registry: ModelRegistry | None = None,
) -> ModelCard | None:
    registry = registry or ModelRegistry.read_only(DEMO_REGISTRY)
    return registry.production(name)
