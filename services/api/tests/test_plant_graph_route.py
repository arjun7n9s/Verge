"""Plant graph sync API."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_plant_graph_sync_degrades_without_neo4j():
    r = client.post("/api/plant/graph-sync")
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
