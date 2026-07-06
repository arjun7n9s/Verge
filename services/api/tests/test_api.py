"""API contract: lifecycle is enforced, feedback measures FPR, audit verifies."""

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_plant_geojson_serves_demo_layout() -> None:
    r = client.get("/api/plant/geojson")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["properties"]["plant"] == "vizag-coke-oven"
    assert len(body["features"]) == 5
    assert len(body["sensors"]) >= 3
    zone_ids = {f["properties"]["zoneId"] for f in body["features"]}
    assert "B-04" in zone_ids


def test_health_reports_audit_and_llm() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["audit"]["verified"] is True
    assert "provider" in body["llm"]


def test_findings_seeded_in_multiple_states() -> None:
    states = {f["state"] for f in client.get("/api/findings").json()}
    assert {"new", "acknowledged", "snoozed", "escalated", "resolved"} <= states


def test_legal_transition_updates_and_audits() -> None:
    before = len(client.get("/api/audit?limit=999").json())
    r = client.post(
        "/api/findings/F-NEW-01/transition", json={"to": "acknowledged", "actor": "maya"}
    )
    assert r.status_code == 200
    assert r.json()["state"] == "acknowledged"
    after = len(client.get("/api/audit?limit=999").json())
    assert after == before + 1
    # audit still verifies after the append
    assert client.get("/health").json()["audit"]["verified"] is True


def test_illegal_transition_is_409() -> None:
    r = client.post("/api/findings/F-RES-01/transition", json={"to": "new", "actor": "maya"})
    assert r.status_code == 409


def test_snooze_without_reason_is_409() -> None:
    r = client.post("/api/findings/F-ACK-02/transition", json={"to": "snoozed", "actor": "maya"})
    assert r.status_code == 409


def test_feedback_drives_fpr() -> None:
    r = client.post("/api/findings/F-CONV-07/feedback", json={"actor": "maya", "verdict": "useful"})
    assert r.status_code == 200
    assert r.json()["fpr"] == 0.0
    client.post("/api/findings/F-NEW-01/feedback",
                json={"actor": "maya", "verdict": "false-alarm", "reasonCode": "noise"})
    assert client.post("/api/findings/F-ACK-01/feedback",
                       json={"actor": "maya", "verdict": "useful"}).json()["fpr"] > 0


def test_ribbon_text() -> None:
    txt = client.get("/api/sensors/ribbon").json()["text"]
    assert "live" in txt and "stale" in txt


def test_respond_drafts_advisory_and_audits() -> None:
    before = len(client.get("/api/audit?limit=999").json())
    r = client.post("/api/findings/F-CONV-07/respond")
    assert r.status_code == 200
    body = r.json()
    assert body["action"]["advisory"] is True
    assert body["action"]["kind"] == "recommend-permit-pause"
    assert body["alert"]["languages"] == ["en", "hi", "te"]
    assert body["report"]["submitted"] is False  # P8: never auto-submitted
    # three advisory audit entries appended (recommendation, alert, evidence)
    after = len(client.get("/api/audit?limit=999").json())
    assert after == before + 3
    assert client.get("/health").json()["audit"]["verified"] is True


def test_respond_unknown_finding_is_404() -> None:
    assert client.post("/api/findings/NOPE/respond").status_code == 404


def test_shadow_findings_hidden_from_operator_feed() -> None:
    shadow = {
        "findingId": "F-SHADOW-1", "createdAt": "2025-01-13T06:50:00Z", "zoneId": "B-04",
        "title": "shadow convergence", "state": "new", "confidence": 0.85,
        "leadTimeBand": "NEAR", "estimateQuality": "high", "lineage": ["reading:LEL-09"],
        "shadow": True,
    }
    assert client.post("/api/findings", json=shadow).status_code == 200

    live = client.get("/api/findings").json()  # default feed: live only
    assert all(f["findingId"] != "F-SHADOW-1" for f in live)

    shadow_feed = client.get("/api/findings?shadow=true").json()
    assert any(f["findingId"] == "F-SHADOW-1" for f in shadow_feed)

    summary = client.get("/api/shadow/summary").json()
    assert summary["shadow"] >= 1
    assert summary["byBand"].get("NEAR", 0) >= 1
