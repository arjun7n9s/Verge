"""Vision: PPE / person / zone-intrusion CV detector plane (spec §5).

Deterministic classic-CV detections feed compound findings as ``frame`` lineage
legs (P1/P3). Degraded-by-default with no GPU/model — honest, never fabricated.
"""

from pathlib import Path

from .detect import (
    LABELS,
    PERSON,
    PPE_MISSING,
    ZONE_INTRUSION,
    AnnotationDetector,
    Detection,
    StubDetector,
    VisionDetector,
    VisionResult,
    load_annotations,
    provider_from_env,
    to_contributing_signals,
)

SAMPLE_ANNOTATIONS = Path(__file__).parent / "samples" / "vizag-ppe.json"

__all__ = [
    "LABELS",
    "PERSON",
    "PPE_MISSING",
    "SAMPLE_ANNOTATIONS",
    "ZONE_INTRUSION",
    "AnnotationDetector",
    "Detection",
    "StubDetector",
    "VisionDetector",
    "VisionResult",
    "load_annotations",
    "provider_from_env",
    "to_contributing_signals",
]
__version__ = "0.3.0"
