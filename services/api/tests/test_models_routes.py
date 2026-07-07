"""Model registry API + ops integration (spec §14 Phase 4)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_models_list_and_summary():
    body = client.get("/api/models").json()
    assert body["summary"]["total"] >= 1
    # The bundled demo has one production compound-risk model.
    assert body["summary"]["production"].get("compound-risk")
    assert any(m["stage"] == "production" for m in body["models"])


def test_models_stage_filter():
    shadow = client.get("/api/models?stage=shadow").json()
    assert all(m["stage"] == "shadow" for m in shadow["models"])


def test_ops_status_includes_model_registry():
    body = client.get("/api/ops/status").json()
    assert body["modelRegistry"]["total"] >= 1
    assert "production" in body["modelRegistry"]


def test_metrics_includes_models_total():
    assert "verge_models_total" in client.get("/metrics").text


def test_model_route_defaults_to_production():
    body = client.get("/api/models/route?name=compound-risk").json()
    assert body["routed"] is True
    assert body["stage"] == "production"


def test_model_route_unknown_is_degraded():
    body = client.get("/api/models/route?name=does-not-exist").json()
    assert body["routed"] is False
