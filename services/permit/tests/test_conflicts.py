"""SIMOPS detection: time overlap AND spatial relation, with lineage to both permits."""

from datetime import UTC, datetime, timedelta

from verge_permit import conflict_findings, detect_conflicts
from verge_schema.core import Permit

T0 = datetime(2025, 1, 13, 6, 0, tzinfo=UTC)
ADJ = {"B-04": {"B-05"}, "B-05": {"B-04"}}


def _permit(pid: str, kind: str, zone: str, start_min: float, dur_min: float = 60.0) -> Permit:
    return Permit(
        permit_id=pid, kind=kind, zone_id=zone,
        valid_from=T0 + timedelta(minutes=start_min),
        valid_to=T0 + timedelta(minutes=start_min + dur_min),
        status="open",
    )


def test_hotwork_confined_space_adjacent_is_critical() -> None:
    permits = [
        _permit("PW-1", "hot-work", "B-04", 0),
        _permit("PW-2", "confined-space", "B-05", 10),  # adjacent zone, overlapping
    ]
    conflicts = detect_conflicts(permits, adjacency=ADJ)
    assert len(conflicts) == 1
    assert conflicts[0].severity == "critical"
    assert conflicts[0].kinds == frozenset({"hot-work", "confined-space"})


def test_no_conflict_when_not_time_overlapping() -> None:
    permits = [
        _permit("PW-1", "hot-work", "B-04", 0, dur_min=5),
        _permit("PW-2", "confined-space", "B-04", 30),  # starts after PW-1 ends
    ]
    assert detect_conflicts(permits, adjacency=ADJ) == []


def test_no_conflict_when_spatially_far() -> None:
    permits = [
        _permit("PW-1", "hot-work", "B-04", 0),
        _permit("PW-2", "confined-space", "Z-99", 10),  # not adjacent to B-04
    ]
    assert detect_conflicts(permits, adjacency=ADJ) == []


def test_same_zone_required_pair_ignores_adjacency() -> None:
    # hot-work + line-breaking requires SAME_ZONE; adjacent should NOT conflict.
    adj = {"B-04": {"B-05"}}
    far = [_permit("A", "hot-work", "B-04", 0), _permit("B", "line-breaking", "B-05", 5)]
    assert detect_conflicts(far, adjacency=adj) == []
    same = [_permit("A", "hot-work", "B-04", 0), _permit("B", "line-breaking", "B-04", 5)]
    assert len(detect_conflicts(same, adjacency=adj)) == 1


def test_unknown_pair_does_not_conflict() -> None:
    permits = [_permit("A", "loto", "B-04", 0), _permit("B", "loto", "B-04", 5)]
    assert detect_conflicts(permits) == []  # {loto, loto} not in the matrix


def test_closed_permit_excluded() -> None:
    p1 = _permit("A", "hot-work", "B-04", 0)
    p2 = _permit("B", "confined-space", "B-04", 5)
    p2.status = "closed"
    assert detect_conflicts([p1, p2]) == []


def test_conflict_finding_carries_both_permits_in_lineage() -> None:
    permits = [_permit("PW-1", "hot-work", "B-04", 0), _permit("PW-2", "confined-space", "B-04", 5)]
    findings = conflict_findings(permits, adjacency=ADJ, at=T0)
    assert len(findings) == 1
    f = findings[0]
    assert f.lineage == ["permit:PW-1", "permit:PW-2"]
    assert "SIMOPS" in f.title
    assert {s.ref_id for s in f.contributing_signals} == {"PW-1", "PW-2"}
