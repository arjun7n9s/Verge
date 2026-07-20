"""Live Ops camera registry + snapshot / MJPEG."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_cameras_list_includes_demo_sources():
    from verge_api.main import app

    client = TestClient(app)
    r = client.get("/api/cameras")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 2
    by_id = {c["cameraId"]: c for c in body["cameras"]}
    assert by_id["CAM-B04"]["zoneId"] == "B-04"
    assert by_id["CAM-B04"]["hasSource"] is True
    assert by_id["CAM-B04"]["sourceKind"] == "demo"
    assert by_id["CAM-B04"]["streamPath"] == "/api/cameras/CAM-B04/mjpeg"
    assert by_id["CAM-B04"]["snapshotPath"] == "/api/cameras/CAM-B04/snapshot"


def test_camera_demo_snapshot_jpeg():
    from verge_api.main import app

    client = TestClient(app)
    r = client.get("/api/cameras/CAM-B04/snapshot")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/jpeg")
    assert r.headers.get("x-verge-demo") == "1"
    assert r.content[:2] == b"\xff\xd8"
    assert len(r.content) > 200


def test_camera_unknown_404():
    from verge_api.main import app

    client = TestClient(app)
    assert client.get("/api/cameras/CAM-NOPE/snapshot").status_code == 404


def test_camera_mjpeg_frame_generator():
    """Unit-test MJPEG frame yield (HTTP stream is infinite — don't hit it in CI)."""
    from verge_api.camera_stream import grab_snapshot, mjpeg_frames

    snap = grab_snapshot("CAM-B05")
    assert snap.ok and snap.jpeg and snap.jpeg[:2] == b"\xff\xd8"
    gen = mjpeg_frames("CAM-B05", interval_s=0.01)
    first = next(gen)
    assert first[:2] == b"\xff\xd8"
    gen.close()
