"""Tests for permit upsert route."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_permit_upsert_adds_to_registry() -> None:
    now = datetime.now(UTC)
    body = {
        "permitId": "PW-TEST-1",
        "kind": "hot-work",
        "zoneId": "B-04",
        "validFrom": (now - timedelta(minutes=5)).isoformat(),
        "validTo": (now + timedelta(hours=2)).isoformat(),
        "status": "open",
    }
    r = client.post("/api/permits/upsert", json=body)
    assert r.status_code == 200
    assert r.json()["permitId"] == "PW-TEST-1"
    listed = client.get("/api/permits").json()
    assert any(p["permitId"] == "PW-TEST-1" for p in listed)
