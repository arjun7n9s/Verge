"""Commissioning summary API."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_commission_summary_smoke():
    r = client.get("/api/commission/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["plant"] == "vizag-coke-oven"
    assert "ready" in body
    assert len(body["checks"]) == 6
    assert client.get("/api/commission/summary").json() == body
