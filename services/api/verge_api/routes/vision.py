"""Vision API — PPE / person / zone-intrusion detections (spec §5).

The detector plane is degraded-by-default: with no GPU/model configured the
endpoint returns ``degraded: true`` and no detections, never a fabricated one
(P4). When an annotation or model backend is configured it returns real
detections plus the ``frame`` contributing signals they map to, so the console
can show vision as one leg of a compound finding (P3).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from verge_vision import to_contributing_signals

from ..frame_cache import get_frame, store_frame
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


def run_detect(
    app_state,
    detector,
    camera_id: str,
    frame_id: str | None,
    image: bytes | None,
    *,
    zone_id: str | None = None,
) -> dict:
    """Shared detect path for HTTP routes and the continuous WatchLoop."""
    from ..frame_store import upload_vision_frame

    result = detector.detect(camera_id, frame_id, image)
    signals = to_contributing_signals(result)
    body = result.to_dict()
    frame_meta = None
    if image:
        frame_meta = upload_vision_frame(image, camera_id=camera_id)
    detections = list(body.get("detections") or [])
    # Stamp zone when the worker/client provides one (fusion buffer requires it).
    if zone_id:
        for d in detections:
            if isinstance(d, dict) and not d.get("zoneId"):
                d["zoneId"] = zone_id
    s3_uri = frame_meta.get("uri") if frame_meta else None
    if s3_uri:
        for d in detections:
            if isinstance(d, dict) and not d.get("frameUri"):
                # Temporary; rewritten to HTTP path after record assigns ids.
                d["frameUri"] = s3_uri
        body["frameUpload"] = {
            "bucket": frame_meta.get("bucket"),
            "key": frame_meta.get("key"),
            "storageUri": s3_uri,
        }
    recorded = record_vision_detections(app_state, detections)
    # Prefer browser-fetchable paths over s3:// for console Live Ops stage.
    browser_uri = None
    if image and recorded:
        for ev in recorded:
            path = store_frame(app_state, ev.detection_id, image)
            if path:
                ev.frame_uri = path
                browser_uri = path
        # Keep fusion buffer in sync with rewritten URIs.
        buf = getattr(app_state, "vision_detections", None) or []
        by_id = {e.detection_id: e for e in recorded}
        for i, existing in enumerate(buf):
            if existing.detection_id in by_id:
                buf[i] = by_id[existing.detection_id]
    if browser_uri:
        body["frameUri"] = browser_uri
    elif s3_uri:
        body["frameUri"] = s3_uri
    return {
        **body,
        "contributingSignals": [s.model_dump(by_alias=True, mode="json") for s in signals],
        "fusionCount": len(recorded),
        "detections": [d.model_dump(by_alias=True, mode="json") for d in recorded]
        if recorded
        else detections,
    }


@router.post("/vision/detect")
def detect(body: DetectBody, request: Request) -> dict:
    """Annotation-replay / metadata-only detection (no real frame required)."""
    return run_detect(
        request.app.state, request.app.state.vision, body.cameraId, body.frameId, None
    )


@router.post("/vision/detect-frame")
async def detect_frame(
    request: Request,
    cameraId: str = CAMERA_FORM,
    file: UploadFile = FRAME_FILE,
    zoneId: str | None = Form(None),
) -> dict:
    """Real-frame detection — an uploaded image is run through the configured
    detector (e.g. ``UltralyticsDetector``). This is how live/real CCTV or a
    routed demo clip (``verge vision watch``) reaches the vision plane; the
    stub/annotation backends still degrade or replay exactly as before."""
    image = await file.read()
    return run_detect(
        request.app.state,
        request.app.state.vision,
        cameraId,
        None,
        image,
        zone_id=zoneId,
    )


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


@router.get("/vision/frames/{detection_id}")
def vision_frame_bytes(detection_id: str, request: Request) -> Response:
    """Serve last annotated still for a detection — honest 404 when absent."""
    hit = get_frame(request.app.state, detection_id)
    if hit is None:
        raise HTTPException(404, "frame not in memory cache (upload via detect-frame)")
    data, content_type = hit
    return Response(content=data, media_type=content_type)
