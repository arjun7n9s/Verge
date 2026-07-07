"""Stream status and Redpanda fan-out configuration."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_api.redpanda_fanout import fanout_enabled


def test_stream_status_smoke():
    with TestClient(app) as client:
        r = client.get("/api/stream/status")
        assert r.status_code == 200
        body = r.json()
        assert "subscribers" in body
        assert "redpandaFanout" in body
        assert body["fanoutConfigured"] is fanout_enabled()
