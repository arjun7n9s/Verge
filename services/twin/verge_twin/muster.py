"""Evacuation routing over the zone adjacency graph (spec §4.4).

Deterministic, dependency-free BFS — the same plant graph the SIMOPS detector
uses. Given the affected zones, every zone gets a route to the nearest usable
muster point that avoids affected zones. Honesty rule (P4): a zone that cannot
reach any muster point without crossing an affected zone is flagged
``trapped`` — the plan says so instead of drawing a route through gas.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .plant import PlantModel


@dataclass
class ZoneRoute:
    zone_id: str
    muster_id: str | None
    muster_zone: str | None
    route: list[str] = field(default_factory=list)  # zone path, start included
    trapped: bool = False

    def to_wire(self) -> dict:
        return {
            "zoneId": self.zone_id,
            "musterId": self.muster_id,
            "musterZone": self.muster_zone,
            "route": self.route,
            "hops": max(len(self.route) - 1, 0),
            "trapped": self.trapped,
        }


def _bfs_route(
    start: str,
    targets: dict[str, str],  # muster anchor zone -> muster_id
    adjacency: dict[str, set[str]],
    blocked: set[str],
) -> ZoneRoute:
    """Shortest path from ``start`` to any target zone, never *entering* a
    blocked zone. The start itself may be blocked (people must leave it) —
    but every subsequent hop must be clear.
    """
    if start in targets and start not in blocked:
        return ZoneRoute(start, targets[start], start, [start])

    parent: dict[str, str] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        zone = queue.popleft()
        for nxt in sorted(adjacency.get(zone, set())):  # sorted → deterministic
            if nxt in seen or nxt in blocked:
                continue
            seen.add(nxt)
            parent[nxt] = zone
            if nxt in targets:
                path = [nxt]
                while path[-1] != start:
                    path.append(parent.get(path[-1], start))
                path.reverse()
                return ZoneRoute(start, targets[nxt], nxt, path)
            queue.append(nxt)
    return ZoneRoute(start, None, None, [start], trapped=True)


def evacuation_plan(plant: PlantModel, affected: set[str]) -> dict:
    """Routes for every zone in the plant, given the affected zones.

    Muster points anchored in an affected zone are unusable. Affected zones
    are impassable except as a starting point.
    """
    adjacency = plant.adjacency()
    usable = {
        m.zone_id: m.muster_id
        for m in sorted(plant.muster_points.values(), key=lambda m: m.muster_id)
        if m.zone_id not in affected
    }
    unusable = [
        m.muster_id for m in plant.muster_points.values() if m.zone_id in affected
    ]
    routes = {
        zone_id: _bfs_route(zone_id, usable, adjacency, affected)
        for zone_id in sorted(plant.zones)
    }
    return {
        "affectedZones": sorted(affected),
        "usableMusterPoints": [
            {"musterId": mid, "zoneId": zid, "name": plant.muster_points[mid].name}
            for zid, mid in sorted(usable.items(), key=lambda kv: kv[1])
        ],
        "unusableMusterPoints": sorted(unusable),
        "routes": {z: r.to_wire() for z, r in routes.items()},
        "trappedZones": sorted(z for z, r in routes.items() if r.trapped),
    }
