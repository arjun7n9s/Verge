"""Audit anchor ops routes."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_ops_status_includes_anchor_block() -> None:
    body = client.get("/api/ops/status").json()
    anchor = body["audit"]["anchor"]
    assert "configured" in anchor


def test_anchor_get_and_post_degrade_without_minio() -> None:
    get_body = client.get("/api/ops/audit/anchor").json()
    assert get_body["configured"] is False

    post_body = client.post("/api/ops/audit/anchor").json()
    assert post_body["anchored"] is False
