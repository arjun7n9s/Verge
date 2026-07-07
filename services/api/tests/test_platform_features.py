"""Fatigue metrics and plume API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_fatigue_metrics_smoke():
    r = client.get("/api/fatigue/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "trend" in body
    assert "zones" in body


def test_plume_exclusion_smoke():
    r = client.get("/api/zones/B-04/exclusion")
    assert r.status_code == 200
    assert r.json()["zoneId"] == "B-04"
    assert r.json()["exclusion"]["geometry"]["type"] == "Polygon"


def test_trace_header_on_response():
    r = client.get("/health", headers={"X-Verge-Trace-Id": "abc12345deadbeef"})
    assert r.status_code == 200
    assert r.headers.get("X-Verge-Trace-Id") == "abc12345deadbeef"
