"""Vision API — PPE / person / zone-intrusion detections (spec §5).

The detector plane is degraded-by-default: with no GPU/model configured the
endpoint returns ``degraded: true`` and no detections, never a fabricated one
(P4). When an annotation or model backend is configured it returns real
detections plus the ``frame`` contributing signals they map to, so the console
can show vision as one leg of a compound finding (P3).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from verge_vision import to_contributing_signals

from ..vision_events import list_vision_detections, record_vision_detections

router = APIRouter(tags=["vision"])
FRAME_FILE = File(...)
CAMERA_FORM = Form(...)


class DetectBody(BaseModel):
    cameraId: str
    frameId: str | None = None


class VisionEventBody(BaseModel):
    cameraId: str
    zoneId: str
    label: str = "ppe-missing"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


def _detect_response(
    request: Request,
    detector,
    camera_id: str,
    frame_id: str | None,
    image: bytes | None,
) -> dict:
    from ..frame_store import upload_vision_frame

    result = detector.detect(camera_id, frame_id, image)
    signals = to_contributing_signals(result)
    body = result.to_dict()
    frame_meta = None
    if image:
        frame_meta = upload_vision_frame(image, camera_id=camera_id)
    detections = list(body.get("detections") or [])
    if frame_meta and frame_meta.get("uri"):
        uri = frame_meta["uri"]
        for d in detections:
            if isinstance(d, dict) and not d.get("frameUri"):
                d["frameUri"] = uri
        body["frameUri"] = uri
        body["frameUpload"] = {
            "bucket": frame_meta.get("bucket"),
            "key": frame_meta.get("key"),
        }
    recorded = record_vision_detections(request.app.state, detections)
    return {
        **body,
        "contributingSignals": [s.model_dump(by_alias=True, mode="json") for s in signals],
        "fusionCount": len(recorded),
    }


@router.post("/vision/detect")
def detect(body: DetectBody, request: Request) -> dict:
    """Annotation-replay / metadata-only detection (no real frame required)."""
    return _detect_response(
        request, request.app.state.vision, body.cameraId, body.frameId, None
    )


@router.post("/vision/detect-frame")
async def detect_frame(
    request: Request,
    cameraId: str = CAMERA_FORM,
    file: UploadFile = FRAME_FILE,
) -> dict:
    """Real-frame detection — an uploaded image is run through the configured
    detector (e.g. ``UltralyticsDetector``). This is how live/real CCTV or a
    routed demo clip (``verge vision watch``) reaches the vision plane; the
    stub/annotation backends still degrade or replay exactly as before."""
    image = await file.read()
    return _detect_response(request, request.app.state.vision, cameraId, None, image)


@router.post("/vision/events")
def vision_event_ingest(body: VisionEventBody, request: Request) -> dict:
    """Manual/demo vision event for fusion drills (honest about source)."""
    recorded = record_vision_detections(
        request.app.state,
        [
            {
                "label": body.label,
                "zoneId": body.zoneId,
                "cameraId": body.cameraId,
                "confidence": body.confidence,
                "ts": datetime.now(UTC).isoformat(),
            }
        ],
    )
    return {
        "detections": [d.model_dump(by_alias=True, mode="json") for d in recorded],
        "count": len(recorded),
    }


@router.get("/vision/events")
def vision_events_recent(request: Request, limit: int = 50) -> dict:
    events = list_vision_detections(request.app.state, limit=limit)
    return {
        "detections": [d.model_dump(by_alias=True, mode="json") for d in events],
        "count": len(events),
    }
