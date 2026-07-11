"""Real incident replay routes for the console Replay view (spec §10)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)

ALL_INCIDENTS = {
    "vizag-2025-01",
    "bp-texas-city-2005",
    "jaipur-ioc-2009",
    "synthetic-nearmiss-01",
}


def test_list_replays_returns_all_four():
    r = client.get("/api/replays")
    assert r.status_code == 200
    body = r.json()
    assert {row["incidentId"] for row in body} == ALL_INCIDENTS
    for row in body:
        assert row["title"]
        assert row["zoneId"]
        assert row["breachTs"]


def test_get_replay_unknown_incident_404():
    r = client.get("/api/replays/not-a-real-incident")
    assert r.status_code == 404


def test_get_replay_has_real_verge_alert_and_breach_events():
    r = client.get("/api/replays/vizag-2025-01")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "vizag-2025-01"
    assert body["leadMin"] is not None and body["leadMin"] > 15
    assert body["band"] in {"NEAR", "IMMINENT"}
    assert body["duration"] > 0

    kinds = {e["type"] for e in body["events"]}
    assert "breach" in kinds
    assert "verge-alert" in kinds
    assert "reading" in kinds

    # Verge's alert must land strictly before the breach on the timeline.
    breach_time = next(e["time"] for e in body["events"] if e["type"] == "breach")
    alert_time = next(e["time"] for e in body["events"] if e["type"] == "verge-alert")
    assert alert_time < breach_time

    # Events are chronological.
    times = [e["time"] for e in body["events"]]
    assert times == sorted(times)


def test_every_replay_is_fetchable_and_consistent_with_the_eval_harness():
    from eval.harness import run_incident

    for incident in ALL_INCIDENTS:
        r = client.get(f"/api/replays/{incident}")
        assert r.status_code == 200
        body = r.json()
        harness = run_incident(incident)
        assert body["leadMin"] == harness["verge"]["leadMin"]
        assert body["band"] == harness["verge"]["band"]
