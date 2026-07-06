"""Tests for shift handover report route."""

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_shift_handover_report_drafts_and_audits() -> None:
    before = len(client.get("/api/audit?limit=999").json())
    r = client.post(
        "/api/reports/shift-handover",
        json={"actor": "maya", "notes": "B-04 LEL rising, hot work still open."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["submitted"] is False
    assert "SHIFT HANDOVER" in body["markdown"]
    assert isinstance(body["openFindings"], list)
    after = client.get("/api/audit?limit=999").json()
    assert len(after) == before + 1
    assert after[-1]["kind"] == "shift-handover-report"
