"""Compliance API routes (spec §5)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_compliance_report_shape_and_pack():
    r = client.get("/api/compliance/report")
    assert r.status_code == 200
    body = r.json()
    assert body["plant"]
    assert 0.0 < body["coverageRatio"] <= 1.0
    assert body["clauses"]
    pack = body["evidencePack"]
    assert len(pack["manifestHash"]) == 64
    # The pack binds to the live audit head (P6).
    assert pack["auditHead"]


def test_compliance_report_is_deterministic():
    a = client.get("/api/compliance/report").json()
    b = client.get("/api/compliance/report").json()
    # Same clause verdicts and coverage across calls (LLM-free, reproducible).
    assert a["coverageRatio"] == b["coverageRatio"]
    assert [c["status"] for c in a["clauses"]] == [c["status"] for c in b["clauses"]]


def test_compliance_gaps_are_regulatory_gap_payloads():
    body = client.get("/api/compliance/gaps").json()
    assert body["gaps"]
    for g in body["gaps"]:
        assert g["kind"] == "regulatory-gap"
        assert g["standard"]


def test_incident_report_for_seeded_finding():
    fid = client.get("/api/findings").json()[0]["findingId"]
    r = client.get(f"/api/findings/{fid}/incident-report")
    assert r.status_code == 200
    body = r.json()
    assert body["findingId"] == fid
    assert len(body["manifestHash"]) == 64
    assert body["auditHead"]  # bound to the live audit chain
    assert "Incident report" in body["markdown"]
    # A seeded finding has at least its creation event in the timeline.
    assert body["timeline"]


def test_incident_report_unknown_finding_404():
    assert client.get("/api/findings/NOPE/incident-report").status_code == 404


def test_compliance_changes_vs_baseline():
    body = client.get("/api/compliance/changes").json()
    assert body["changed"] is True
    assert "VC-GAS-DETECTION" in body["added"]
    assert body["fingerprintFrom"] != body["fingerprintTo"]
