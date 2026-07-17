"""Live plant graph projection — never fabricated demo nodes."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app


def test_plant_graph_returns_live_projection() -> None:
    client = TestClient(app)
    r = client.get("/api/plant/graph")
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body and "links" in body
    assert body["source"] == "twin+permits+findings"
    assert body["degraded"] is False
    # Seeded demo has open permits + findings → expect some nodes.
    assert len(body["nodes"]) >= 1
    types = {n["type"] for n in body["nodes"]}
    assert types <= {"equipment", "permit", "risk"}
    # No hardcoded Vizag fiction labels from the old console mock.
    labels = " ".join(n["label"] for n in body["nodes"])
    assert "Primary Reformer Line-04" not in labels
    assert "RF-0491" not in labels
