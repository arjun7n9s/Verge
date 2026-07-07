"""MLOps: model registry (shadow/canary/production) + drift detection (spec §14 P4).

Dependency-free and file-backed so it version-controls and ships inside an
air-gapped bundle. The ML layer gets the same lifecycle discipline as findings:
nothing reaches production without passing shadow + canary first.
"""

from .artifacts import (
    ArtifactError,
    artifact_root,
    load_sklearn_bundle,
    production_model,
    resolve_artifact_path,
    sha256_file,
    verify_artifact,
)
from .canary import parse_canary_zones
from .drift import (
    MODERATE,
    SIGNIFICANT,
    STABLE,
    DriftResult,
    classify,
    population_stability_index,
)
from .registry import (
    CANARY,
    DEMO_REGISTRY,
    PRODUCTION,
    REGISTERED,
    RETIRED,
    SHADOW,
    IllegalPromotion,
    ModelCard,
    ModelRegistry,
)
from .router import ModelRouter, RouteDecision


def demo_registry() -> ModelRegistry:
    """The bundled demo registry (in-memory, read-only)."""
    return ModelRegistry.read_only(DEMO_REGISTRY)


__all__ = [
    "parse_canary_zones",
    "ArtifactError",
    "artifact_root",
    "load_sklearn_bundle",
    "production_model",
    "resolve_artifact_path",
    "sha256_file",
    "verify_artifact",
    "CANARY",
    "DEMO_REGISTRY",
    "MODERATE",
    "PRODUCTION",
    "REGISTERED",
    "RETIRED",
    "SHADOW",
    "SIGNIFICANT",
    "STABLE",
    "DriftResult",
    "IllegalPromotion",
    "ModelCard",
    "ModelRegistry",
    "ModelRouter",
    "RouteDecision",
    "classify",
    "demo_registry",
    "population_stability_index",
]
__version__ = "0.3.0"
