"""Tests for shift handover report drafting."""

from datetime import UTC, datetime

from verge_llm import NullProvider
from verge_orchestrator.shift_handover import draft_shift_handover
from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import RiskFinding

T = datetime(2025, 1, 13, 7, 0, tzinfo=UTC)


def _finding(fid: str, state: FindingState) -> RiskFinding:
    return RiskFinding(
        finding_id=fid,
        created_at=T,
        zone_id="B-04",
        title="test",
        state=state,
        confidence=0.8,
        lead_time_band=LeadTimeBand.NEAR,
        estimate_quality=EstimateQuality.HIGH,
        lineage=["reading:LEL-04"],
    )


def test_draft_includes_open_findings_only() -> None:
    findings = [
        _finding("F-OPEN", FindingState.NEW),
        _finding("F-DONE", FindingState.RESOLVED),
    ]
    draft = draft_shift_handover(
        findings, notes="handover note", at=T, provider=NullProvider()
    )
    assert draft.open_findings == ["F-OPEN"]
    assert draft.submitted is False
    assert "handover note" in draft.markdown
