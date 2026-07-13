"""Evacuation routing: BFS away from affected zones, honest trapped flags."""

from __future__ import annotations

from verge_twin import DEMO_PLANT, load_plant
from verge_twin.muster import evacuation_plan

PLANT = load_plant(DEMO_PLANT)  # B-01..B-05 in a row; MP-WEST@B-01, MP-EAST@B-05


def test_routes_avoid_affected_zone():
    plan = evacuation_plan(PLANT, {"B-04"})
    # B-05 must NOT route west through affected B-04 — its own muster point
    # (MP-EAST) anchors in B-05 itself.
    b5 = plan["routes"]["B-05"]
    assert b5["musterId"] == "MP-EAST"
    assert b5["route"] == ["B-05"]
    assert not b5["trapped"]
    # B-03 heads west, away from B-04.
    b3 = plan["routes"]["B-03"]
    assert b3["musterId"] == "MP-WEST"
    assert b3["route"] == ["B-03", "B-02", "B-01"]
    assert "B-04" not in b3["route"]


def test_affected_zone_gets_route_out():
    plan = evacuation_plan(PLANT, {"B-04"})
    b4 = plan["routes"]["B-04"]
    # People in the affected zone still get a route — leaving is the point.
    assert not b4["trapped"]
    assert b4["route"][0] == "B-04"
    assert b4["musterId"] in {"MP-WEST", "MP-EAST"}
    assert all(z != "B-04" for z in b4["route"][1:])


def test_muster_point_in_affected_zone_is_unusable():
    plan = evacuation_plan(PLANT, {"B-05"})
    assert "MP-EAST" in plan["unusableMusterPoints"]
    assert all(m["musterId"] != "MP-EAST" for m in plan["usableMusterPoints"])
    # Everyone routes west now.
    assert plan["routes"]["B-04"]["musterId"] == "MP-WEST"


def test_trapped_zone_is_flagged_not_routed_through_gas():
    # Affect B-02 AND B-04: B-03 is boxed in (linear row) — it must be flagged
    # trapped, never given a route through an affected zone.
    plan = evacuation_plan(PLANT, {"B-02", "B-04"})
    b3 = plan["routes"]["B-03"]
    assert b3["trapped"] is True
    assert b3["musterId"] is None
    assert plan["trappedZones"] == ["B-03"]


def test_plan_is_deterministic():
    a = evacuation_plan(PLANT, {"B-04"})
    b = evacuation_plan(PLANT, {"B-04"})
    assert a == b
