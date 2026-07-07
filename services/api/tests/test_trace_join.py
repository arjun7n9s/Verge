"""End-to-end trace join tests."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_api.trace_index import TraceIndex
from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import RiskFinding

client = TestClient(app)
TRACE = "feedface12345678"


def _finding(fid: str) -> RiskFinding:
    now = datetime.now(UTC)
    return RiskFinding(
        finding_id=fid,
        created_at=now,
        zone_id="B-04",
        title="trace test",
        state=FindingState.NEW,
        confidence=0.9,
        lead_time_band=LeadTimeBand.NEAR,
        estimate_quality=EstimateQuality.MEDIUM,
    )


def test_trace_header_echoed_and_indexed_on_reading_ingest() -> None:
    r = client.post(
        "/api/readings/ingest",
        headers={"X-Verge-Trace-Id": TRACE},
        json={
            "ts": "2025-01-01T06:40:00+00:00",
            "sensorId": "LEL-99",
            "kind": "gas-lel",
            "unit": "%LEL",
            "zoneId": "B-04",
            "value": 12.0,
        },
    )
    assert r.status_code == 200
    assert r.headers.get("X-Verge-Trace-Id") == TRACE

    join = client.get(f"/api/ops/trace/{TRACE}").json()
    assert join["traceId"] == TRACE
    assert any(s["stage"] == "api.readings.ingest" for s in join["spans"])


def test_finding_ingest_records_trace_and_audit_payload() -> None:
    r = client.post(
        "/api/findings",
        headers={"X-Verge-Trace-Id": TRACE},
        json=_finding("F-TRACE-1").model_dump(by_alias=True, mode="json"),
    )
    assert r.status_code == 200
    join = client.get(f"/api/ops/trace/{TRACE}").json()
    assert any(s["stage"] == "api.findings.ingest" for s in join["spans"])
    assert join["auditHits"] >= 1


def test_trace_index_lookup_empty_for_unknown() -> None:
    idx = TraceIndex()
    assert idx.lookup("does-not-exist") == []
