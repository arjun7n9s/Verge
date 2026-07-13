"""OccupancyTracker: zone presence, staleness honesty, exposure math."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from verge_twin import OccupancyTracker

T0 = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)


def _fix(worker: str, zone: str, ts: datetime, **extra) -> dict:
    return {"type": "worker-location", "workerId": worker, "zoneId": zone,
            "ts": ts.isoformat(), **extra}


def test_latest_fix_wins_and_out_of_order_ignored():
    occ = OccupancyTracker()
    occ.ingest(_fix("W-1", "B-01", T0))
    occ.ingest(_fix("W-1", "B-02", T0 + timedelta(minutes=2)))
    # A replayed older fix must not move the worker backwards.
    occ.ingest(_fix("W-1", "B-05", T0 - timedelta(minutes=5)))
    positions = occ.positions(now=T0 + timedelta(minutes=3))
    assert len(positions) == 1
    assert positions[0]["zoneId"] == "B-02"


def test_name_role_survive_sparse_updates():
    occ = OccupancyTracker()
    occ.ingest(_fix("W-1", "B-01", T0, name="S. Rao", role="welder"))
    occ.ingest(_fix("W-1", "B-02", T0 + timedelta(minutes=1)))  # bare RTLS ping
    w = occ.positions(now=T0 + timedelta(minutes=1))[0]
    assert w["name"] == "S. Rao"
    assert w["role"] == "welder"


def test_staleness_flagged_never_dropped():
    occ = OccupancyTracker(stale_after_s=300)
    occ.ingest(_fix("W-1", "B-04", T0))
    now = T0 + timedelta(minutes=10)
    positions = occ.positions(now=now)
    assert positions[0]["stale"] is True
    assert positions[0]["ageS"] == 600.0
    # Still present in the zone roster — last-known-location is muster-critical.
    assert occ.zone_roster(now=now)["B-04"][0]["workerId"] == "W-1"


def test_exposure_counts_zone_and_adjacent_separately():
    occ = OccupancyTracker(stale_after_s=300)
    now = T0 + timedelta(minutes=1)
    occ.ingest(_fix("W-1", "B-04", T0, role="welder"))
    occ.ingest(_fix("W-2", "B-04", T0))
    occ.ingest(_fix("W-3", "B-03", T0))  # adjacent
    occ.ingest(_fix("W-4", "B-01", T0))  # far away
    exp = occ.exposure({"B-04"}, {"B-03", "B-05"}, now=now)
    assert [w["workerId"] for w in exp["inZone"]] == ["W-1", "W-2"]
    assert [w["workerId"] for w in exp["inAdjacent"]] == ["W-3"]
    assert exp["headcountAtRisk"] == 3
    assert exp["staleFixes"] == 0


def test_exposure_counts_stale_fix_in_risk_zone():
    """A tag that went dark inside the risk zone is still at-risk headcount."""
    occ = OccupancyTracker(stale_after_s=60)
    occ.ingest(_fix("W-1", "B-04", T0))
    exp = occ.exposure({"B-04"}, set(), now=T0 + timedelta(minutes=30))
    assert exp["headcountAtRisk"] == 1
    assert exp["staleFixes"] == 1
