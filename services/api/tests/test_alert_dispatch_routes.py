"""Alert dispatch API (spec §4.4, P8)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def _finding_id() -> str:
    return client.get("/api/findings").json()[0]["findingId"]


def test_dispatch_requires_approver():
    fid = _finding_id()
    r = client.post(f"/api/findings/{fid}/alert/dispatch", json={"channels": ["console"]})
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is True
    assert body["anyDelivered"] is False


def test_dispatch_with_approver_delivers_to_console():
    fid = _finding_id()
    r = client.post(f"/api/findings/{fid}/alert/dispatch",
                    json={"approvedBy": "maya", "channels": ["console", "sms"]})
    body = r.json()
    assert body["refused"] is False
    assert body["approvedBy"] == "maya"
    by_channel = {x["channel"]: x for x in body["results"]}
    assert by_channel["console"]["delivered"] is True
    assert by_channel["sms"]["degraded"] is True


def test_dispatch_is_audit_chained():
    fid = _finding_id()
    before = client.get("/health").json()["audit"]["entries"]
    client.post(f"/api/findings/{fid}/alert/dispatch",
                json={"approvedBy": "maya", "channels": ["console"]})
    after = client.get("/health").json()["audit"]["entries"]
    assert after > before
    assert client.get("/health").json()["audit"]["verified"] is True


def test_dispatch_unknown_finding_404():
    r = client.post("/api/findings/NOPE/alert/dispatch", json={"approvedBy": "maya"})
    assert r.status_code == 404
