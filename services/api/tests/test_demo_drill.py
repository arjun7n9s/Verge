"""Compound demo drill — pack-driven publishers → live fusion (no UI fiction)."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def test_demo_scenario_meta():
    from verge_api.main import app

    client = TestClient(app)
    r = client.get("/api/demo/scenarios/compound-drill")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "compound-drill"
    assert "multi-source" in body["label"].lower()
    assert body["radioCues"] >= 6


def test_demo_status_exposes_phase_coach_fields():
    from verge_api.demo_scenario import load_scenario
    from verge_api.main import app
    from verge_api.watch_loop import controller

    pack = load_scenario("compound-drill")
    early = pack.phase_at(10)
    assert early["phaseId"] == "baseline"
    weak = pack.phase_at(90)
    assert weak["phaseId"] == "weak-smell"
    assert "alarm" in weak["phaseHint"].lower()

    client = TestClient(app)
    if controller.status.running:
        client.post("/api/demo/stop")
    start = client.post(
        "/api/demo/start",
        json={
            "scenarioId": "compound-drill-ci",
            "intervalS": 1.0,
            "vision": False,
            "voice": False,
            "sensors": True,
            "fuse": False,
            "cognee": False,
            "workers": False,
        },
    )
    assert start.status_code == 200
    watch = start.json()["watch"]
    assert watch["mode"] == "demo"
    assert watch.get("phaseId")
    assert watch.get("phaseLabel")
    assert watch.get("phaseHint")
    assert isinstance(watch.get("phases"), list) and len(watch["phases"]) >= 4
    stop = client.post("/api/demo/stop")
    assert stop.status_code == 200


def test_demo_start_compound_ci_persists_multi_source_finding():
    from verge_api.main import app
    from verge_api.watch_loop import controller

    client = TestClient(app)
    if controller.status.running:
        client.post("/api/demo/stop")

    r = client.post(
        "/api/demo/start",
        json={
            "scenarioId": "compound-drill-ci",
            "intervalS": 1.0,
            "vision": True,
            "voice": True,
            "sensors": True,
            "fuse": True,
            "cognee": False,
            "workers": True,
        },
    )
    assert r.status_code == 200
    watch = r.json()["watch"]
    assert watch["running"] is True
    assert watch["mode"] == "demo"
    assert watch["scenarioId"] == "compound-drill-ci"

    # Permit seeded for SIMOPS / hot-work predicates
    permits = client.get("/api/permits").json()
    assert any(
        (p.get("kind") == "hot-work" and p.get("zoneId") == "B-04")
        or (p.get("kind") == "hot-work" and p.get("zone_id") == "B-04")
        for p in permits
    )

    deadline = time.time() + 55
    status = {}
    compound = None
    while time.time() < deadline:
        status = client.get("/api/watch/status").json()
        counts = status.get("counts") or {}
        voice_ok = counts.get("voiceEvents", 0) >= 1
        sensor_ok = counts.get("sensorReads", 0) >= 2
        vision_ok = counts.get("visionDetections", 0) >= 1 or counts.get(
            "visionFrames", 0
        ) >= 1
        if voice_ok and sensor_ok and vision_ok and counts.get("findingsPersisted", 0) >= 1:
            findings = client.get("/api/findings").json()
            rows = findings if isinstance(findings, list) else findings.get("findings") or []
            for f in rows:
                title = (f.get("title") or "").lower()
                lineage = f.get("lineage") or []
                kinds = {str(x).split(":")[0] for x in lineage}
                multi = {"voice", "reading", "vision"} <= kinds
                if "compound" in title and multi:
                    compound = f
                    break
            if compound:
                break
        if status.get("lastError"):
            break
        time.sleep(0.5)

    stop = client.post("/api/demo/stop")
    assert stop.status_code == 200
    assert stop.json()["watch"]["running"] is False

    assert status.get("counts", {}).get("voiceEvents", 0) >= 1
    assert status.get("counts", {}).get("sensorReads", 0) >= 2
    assert (
        status.get("counts", {}).get("visionDetections", 0) >= 1
        or status.get("counts", {}).get("visionFrames", 0) >= 1
    )
    assert compound is not None, (
        f"expected compound multi-source finding; status={status} last={status.get('last')}"
    )
