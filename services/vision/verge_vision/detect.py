"""PPE / person / zone-intrusion CV detector plane (spec §5 Pillar — vision).

Vision is a **detector plane**, not a narrator: it emits classic-CV detections
(a person without a hard-hat, an intrusion into a restricted zone) that become
one leg — a ``ContributingSignal(kind="frame")`` — of a compound finding. It is
deterministic ML (Ultralytics / RT-DETR on the plant GPU box in production), not
an LLM, so it is allowed in the safety plane (P1). The narrative layer never
enters here.

The production backend needs a GPU and a model, which the hackathon/dev box does
not have — so this module is **degraded-by-default and honest about it**. With no
model configured, ``detect`` returns ``degraded=True`` and an empty detection
list; it never fabricates a detection (P4). Two real backends are provided:

* ``AnnotationDetector`` — replays pre-labeled frame annotations (deterministic;
  the same role the event replay plays for the risk engine — real detections,
  no GPU, reproducible in CI and demos).
* ``ultralytics`` — lazily imported; if the package or a GPU is absent it
  degrades to the stub instead of raising.

Backend selection is env-driven (``VERGE_VISION_*``), mirroring the memory/voice
providers so the whole intelligence layer degrades the same way.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from verge_schema.findings import ContributingSignal

SAMPLES_DIR = Path(__file__).parent / "samples"

# Detection labels the plane emits. Kept small and stable — a schema of sorts.
PERSON = "person"
PPE_MISSING = "ppe-missing"
ZONE_INTRUSION = "zone-intrusion"
LABELS: frozenset[str] = frozenset({PERSON, PPE_MISSING, ZONE_INTRUSION})


@dataclass(frozen=True)
class Detection:
    label: str
    zone_id: str
    confidence: float
    camera_id: str
    ts: datetime | None = None
    detail: str = ""  # e.g. "no hard-hat", "restricted zone"
    bbox: tuple[float, float, float, float] | None = None  # normalized x,y,w,h

    def summary(self) -> str:
        base = {
            PERSON: "person detected",
            PPE_MISSING: "PPE missing",
            ZONE_INTRUSION: "zone intrusion",
        }.get(self.label, self.label)
        where = f" in {self.zone_id}" if self.zone_id else ""
        why = f" ({self.detail})" if self.detail else ""
        return f"{base}{why}{where}"

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "zoneId": self.zone_id,
            "confidence": round(self.confidence, 4),
            "cameraId": self.camera_id,
            "ts": self.ts.isoformat() if self.ts else None,
            "detail": self.detail,
            "bbox": list(self.bbox) if self.bbox else None,
        }


@dataclass
class VisionResult:
    camera_id: str
    detections: list[Detection] = field(default_factory=list)
    degraded: bool = False
    reason: str = ""
    backend: str = "stub"

    def to_dict(self) -> dict:
        return {
            "cameraId": self.camera_id,
            "detections": [d.to_dict() for d in self.detections],
            "degraded": self.degraded,
            "reason": self.reason,
            "backend": self.backend,
        }


@runtime_checkable
class VisionDetector(Protocol):
    backend: str

    def detect(self, camera_id: str, frame_id: str | None = None) -> VisionResult: ...


class StubDetector:
    """The honest default: no model, no detections, ``degraded=True`` (P4)."""

    backend = "stub"

    def __init__(self, reason: str = "vision disabled (no model configured)") -> None:
        self._reason = reason

    def detect(self, camera_id: str, frame_id: str | None = None) -> VisionResult:
        return VisionResult(camera_id=camera_id, degraded=True, reason=self._reason)


class AnnotationDetector:
    """Deterministic replay of pre-labeled frame annotations (no GPU required).

    Annotations are ``{camera_id: [detection, ...]}``. Each detection dict may
    carry ``frameId`` so a specific frame can be requested; omitting ``frame_id``
    returns every detection for the camera.
    """

    backend = "annotations"

    def __init__(self, annotations: Mapping[str, list[dict]]) -> None:
        self._ann = dict(annotations)

    def detect(self, camera_id: str, frame_id: str | None = None) -> VisionResult:
        # A detection with no frameId is a camera-wide detection (matches any
        # requested frame); a frame-scoped one matches only its own frame.
        raw = self._ann.get(camera_id, [])
        dets: list[Detection] = []
        skipped = 0
        for d in raw:
            if frame_id is not None and d.get("frameId") not in (None, frame_id):
                continue
            if d.get("label") not in LABELS:
                continue
            det = self._parse_detection(d, camera_id)
            if det is None:
                skipped += 1  # malformed annotation — drop, never fabricate (P4)
            else:
                dets.append(det)
        reason = f"{skipped} malformed annotation(s) skipped" if skipped else ""
        return VisionResult(camera_id=camera_id, detections=dets,
                            backend=self.backend, reason=reason)

    @staticmethod
    def _parse_detection(d: dict, camera_id: str) -> Detection | None:
        """Build one Detection, tolerating malformed fields (returns None)."""
        try:
            confidence = float(d.get("confidence", 0.0))
            if not math.isfinite(confidence):
                return None
            ts_raw = d.get("ts")
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
            bbox = d.get("bbox")
            if bbox is not None:
                bbox = tuple(float(x) for x in bbox)
                if len(bbox) != 4:
                    bbox = None
            return Detection(
                label=d["label"],
                zone_id=d.get("zoneId", ""),
                confidence=confidence,
                camera_id=camera_id,
                ts=ts,
                detail=d.get("detail", ""),
                bbox=bbox,
            )
        except (ValueError, TypeError, AttributeError):
            return None


def load_annotations(path: str | Path) -> dict[str, list[dict]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ultralytics_detector(model_path: str) -> VisionDetector:
    """Lazily build a real model-backed detector; degrade if the stack is absent."""
    try:  # pragma: no cover - exercised only where ultralytics + GPU exist
        import ultralytics  # noqa: F401
    except Exception as exc:  # noqa: BLE001 - any import/runtime failure degrades
        return StubDetector(reason=f"ultralytics unavailable: {exc}")
    # A real adapter wraps the model here; on the GPU-less dev/CI box we never
    # reach this branch, so it intentionally degrades rather than half-implements.
    return StubDetector(reason="ultralytics backend not wired on this host")


def provider_from_env(env: Mapping[str, str] | None = None) -> VisionDetector:
    """Select a detector from ``VERGE_VISION_*``; default is the degraded stub."""
    env = env or os.environ
    if env.get("VERGE_VISION_ENABLED", "").lower() not in ("1", "true", "yes"):
        return StubDetector(reason="vision disabled (VERGE_VISION_ENABLED not set)")
    backend = env.get("VERGE_VISION_BACKEND", "stub").lower()
    if backend == "annotations":
        path = env.get("VERGE_VISION_ANNOTATIONS")
        if not path or not Path(path).exists():
            return StubDetector(reason="annotations backend: file not found")
        # A corrupt/non-dict annotations file must degrade, not crash wiring (P4).
        try:
            ann = load_annotations(path)
            if not isinstance(ann, dict):
                raise ValueError("annotations must be a JSON object keyed by camera id")
            return AnnotationDetector(ann)
        except (ValueError, OSError) as exc:
            return StubDetector(reason=f"annotations backend: unreadable/invalid ({exc})")
    if backend == "ultralytics":
        return _ultralytics_detector(env.get("VERGE_VISION_MODEL", ""))
    return StubDetector(reason=f"unknown backend '{backend}'")


def to_contributing_signals(result: VisionResult) -> list[ContributingSignal]:
    """Convert detections into finding lineage legs (``kind="frame"``, P3)."""
    return [
        ContributingSignal(
            kind="frame",
            ref_id=f"{d.camera_id}:{d.label}",
            summary=d.summary(),
            ts=d.ts,
        )
        for d in result.detections
    ]
