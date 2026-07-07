"""Vision API — PPE / person / zone-intrusion detections (spec §5).

The detector plane is degraded-by-default: with no GPU/model configured the
endpoint returns ``degraded: true`` and no detections, never a fabricated one
(P4). When an annotation or model backend is configured it returns real
detections plus the ``frame`` contributing signals they map to, so the console
can show vision as one leg of a compound finding (P3).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel
from verge_vision import to_contributing_signals

router = APIRouter(tags=["vision"])


class DetectBody(BaseModel):
    cameraId: str
    frameId: str | None = None


@router.post("/vision/detect")
def detect(body: DetectBody, request: Request) -> dict:
    detector = request.app.state.vision
    result = detector.detect(body.cameraId, body.frameId)
    signals = to_contributing_signals(result)
    return {
        **result.to_dict(),
        "contributingSignals": [s.model_dump(by_alias=True, mode="json") for s in signals],
    }
