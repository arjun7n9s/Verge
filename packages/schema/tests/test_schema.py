"""Schema invariants: camelCase wire format, enum vocab, lead-time band bounds."""

from datetime import datetime, timezone

from verge_schema import (
    BAND_BOUNDS_MIN,
    ContributingSignal,
    DataQuality,
    EstimateQuality,
    FindingState,
    LeadTimeBand,
    RiskFinding,
)


def _now() -> datetime:
    return datetime(2025, 1, 13, 6, 44, tzinfo=timezone.utc)


def test_finding_serializes_camel_case() -> None:
    f = RiskFinding(
        finding_id="F-1",
        created_at=_now(),
        zone_id="B-04",
        title="hot-work + gas-drift + shift-changeover",
        confidence=0.82,
        lead_time_band=LeadTimeBand.NEAR,
        estimate_quality=EstimateQuality.HIGH,
        confidence_degraded_by=["CO-04"],
    )
    wire = f.model_dump(by_alias=True)
    # camelCase keys on the wire (contract with the TS types)
    assert "leadTimeBand" in wire
    assert "confidenceDegradedBy" in wire
    assert "finding_id" not in wire
    assert wire["leadTimeBand"] == "NEAR"


def test_round_trip_by_alias() -> None:
    payload = {
        "findingId": "F-2",
        "createdAt": _now().isoformat(),
        "zoneId": "B-04",
        "title": "t",
        "confidence": 0.5,
    }
    f = RiskFinding.model_validate(payload)
    assert f.finding_id == "F-2"
    assert f.state == FindingState.NEW  # default lifecycle entry point


def test_contributing_signal_lineage() -> None:
    sig = ContributingSignal(kind="reading", ref_id="CO-04", summary="drift")
    assert sig.model_dump(by_alias=True)["refId"] == "CO-04"


def test_band_bounds_cover_all_bands() -> None:
    assert set(BAND_BOUNDS_MIN) == set(LeadTimeBand)
    assert BAND_BOUNDS_MIN[LeadTimeBand.NEAR] == (15.0, 45.0)
    assert BAND_BOUNDS_MIN[LeadTimeBand.WATCH][1] is None


def test_data_quality_default_is_live() -> None:
    f = RiskFinding(
        finding_id="F-3", created_at=_now(), zone_id="Z", title="t", confidence=0.1
    )
    assert f.confidence_degraded is False
    assert DataQuality.LIVE.value == "live"
