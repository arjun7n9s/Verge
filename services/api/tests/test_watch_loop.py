"""Continuous WatchLoop — product heartbeat (vision/sensors/fuse)."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def test_watch_status_idle():
    from verge_api.main import app

    client = TestClient(app)
    r = client.get("/api/watch/status")
    assert r.status_code == 200
    body = r.json()
    assert "running" in body
    assert "legs" in body


def test_watch_start_ticks_vision_and_sensors_then_stop():
    from verge_api.main import app
    from verge_api.watch_loop import controller

    client = TestClient(app)
    # Ensure clean slate
    if controller.status.running:
        client.post("/api/watch/stop")

    r = client.post(
        "/api/watch/start",
        json={
            "intervalS": 1.0,
            "vision": True,
            "voice": False,  # no Melia keys required in CI
            "sensors": True,
            "fuse": True,
            "cognee": False,
        },
    )
    assert r.status_code == 200
    assert r.json()["watch"]["running"] is True

    # Wait for ticks (first vision tick may load Ultralytics once).
    deadline = time.time() + 45
    status = {}
    while time.time() < deadline:
        status = client.get("/api/watch/status").json()
        if status.get("ticks", 0) >= 2 and status.get("counts", {}).get("visionFrames", 0) >= 1:
            break
        if status.get("lastError"):
            break
        time.sleep(0.5)

    assert status.get("running") is True
    assert status.get("ticks", 0) >= 2
    assert status["counts"]["visionFrames"] >= 1
    assert status["counts"]["sensorReads"] >= 1

    # Vision events should have landed from demo camera grabs
    events = client.get("/api/vision/events?limit=5").json()
    assert "detections" in events

    stop = client.post("/api/watch/stop")
    assert stop.status_code == 200
    assert stop.json()["watch"]["running"] is False
