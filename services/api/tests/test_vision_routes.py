"""Vision API routes: degraded by default, real detections when configured."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_vision import SAMPLE_ANNOTATIONS, AnnotationDetector, load_annotations


def test_detect_degraded_by_default():
    from verge_api.main import app

    client = TestClient(app)
    r = client.post("/api/vision/detect", json={"cameraId": "CAM-B04"})
    assert r.status_code == 200
    body = r.json()
    # No GPU/model in the default env -> degraded, no fabricated detections.
    assert body["degraded"] is True
    assert body["detections"] == []
    assert body["contributingSignals"] == []


def test_detect_returns_frame_signals_when_backend_configured():
    from verge_api.main import app

    app.state.vision = AnnotationDetector(load_annotations(SAMPLE_ANNOTATIONS))
    try:
        client = TestClient(app)
        body = client.post("/api/vision/detect", json={"cameraId": "CAM-B04"}).json()
        assert body["degraded"] is False
        assert body["detections"]
        signals = body["contributingSignals"]
        assert signals and all(s["kind"] == "frame" for s in signals)
    finally:
        # Restore the degraded default so other tests see the real posture.
        from verge_vision import provider_from_env

        app.state.vision = provider_from_env({})
