"""Tests for permit routes."""

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_list_permits_returns_seeded_open_permits() -> None:
    r = client.get("/api/permits")
    assert r.status_code == 200
    permits = r.json()
    assert len(permits) >= 1
    ids = {p["permitId"] for p in permits}
    assert "PW-2025-0142" in ids


def test_permit_conflicts_endpoint() -> None:
    r = client.get("/api/permits/conflicts")
    assert r.status_code == 200
    body = r.json()
    assert "conflicts" in body
    assert isinstance(body["conflicts"], list)
