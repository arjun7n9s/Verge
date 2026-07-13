"""Zone-level worker occupancy (spec §5 — geospatial heatmap worker layer).

Consumes canonical ``worker-location`` events (omlox-style zone presence from
any RTLS: UWB, BLE, GPS, or access-control badging) and answers the questions
the safety layer actually needs:

- who is in which zone right now, and how fresh is that fix
- how many people are exposed to a finding (its zone + adjacent zones)
- during an emergency: who is accounted for at a muster point and who is
  missing, with their last-known zone (the mustering-industry standard —
  a live roll-call beats a paper roster)

Staleness is honest (P4): a tag not seen for ``stale_after_s`` is flagged
``stale`` with its age, never silently dropped and never shown as a live fix.
Dependency-free and deterministic so it runs on the edge box (P1/P2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts


@dataclass
class WorkerFix:
    worker_id: str
    zone_id: str
    ts: datetime
    name: str = ""
    role: str = ""
    source: str = ""

    def to_wire(self, now: datetime) -> dict:
        age_s = max((now - self.ts).total_seconds(), 0.0)
        return {
            "workerId": self.worker_id,
            "zoneId": self.zone_id,
            "ts": self.ts.isoformat(),
            "name": self.name,
            "role": self.role,
            "source": self.source,
            "ageS": round(age_s, 1),
        }


class OccupancyTracker:
    """Latest zone fix per worker, with staleness accounting."""

    def __init__(self, stale_after_s: float = 300.0) -> None:
        self.stale_after_s = stale_after_s
        self._fixes: dict[str, WorkerFix] = {}

    def ingest(self, event: dict) -> None:
        """Consume one canonical worker-location event (already contract-valid).

        Out-of-order fixes are ignored: a stream replay or a slow provider must
        not move a worker backwards in time.
        """
        fix = WorkerFix(
            worker_id=event["workerId"],
            zone_id=event["zoneId"],
            ts=_parse_ts(event["ts"]),
            name=event.get("name") or "",
            role=event.get("role") or "",
            source=event.get("source") or "",
        )
        current = self._fixes.get(fix.worker_id)
        if current is not None and current.ts > fix.ts:
            return
        # Keep name/role from an earlier richer fix if the update omits them.
        if current is not None:
            fix.name = fix.name or current.name
            fix.role = fix.role or current.role
        self._fixes[fix.worker_id] = fix

    def _wire(self, fix: WorkerFix, now: datetime) -> dict:
        d = fix.to_wire(now)
        d["stale"] = d["ageS"] > self.stale_after_s
        return d

    @property
    def worker_count(self) -> int:
        return len(self._fixes)

    def latest_ts(self) -> datetime | None:
        if not self._fixes:
            return None
        return max(f.ts for f in self._fixes.values())

    def positions(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(UTC)
        return sorted(
            (self._wire(f, now) for f in self._fixes.values()),
            key=lambda d: d["workerId"],
        )

    def zone_roster(self, now: datetime | None = None) -> dict[str, list[dict]]:
        """zone -> workers whose last fix is in that zone (stale ones flagged)."""
        now = now or datetime.now(UTC)
        roster: dict[str, list[dict]] = {}
        for fix in self._fixes.values():
            roster.setdefault(fix.zone_id, []).append(self._wire(fix, now))
        for workers in roster.values():
            workers.sort(key=lambda d: d["workerId"])
        return roster

    def exposure(
        self,
        zones: set[str],
        adjacent: set[str] | None = None,
        now: datetime | None = None,
    ) -> dict:
        """Headcount at risk for a finding: workers in the affected zones plus
        adjacent zones. Stale fixes are counted separately — a worker whose tag
        went dark inside a risk zone is a *bigger* concern, not a smaller one.
        """
        now = now or datetime.now(UTC)
        adjacent = adjacent or set()
        in_zone: list[dict] = []
        in_adjacent: list[dict] = []
        for fix in self._fixes.values():
            if fix.zone_id in zones:
                in_zone.append(self._wire(fix, now))
            elif fix.zone_id in adjacent:
                in_adjacent.append(self._wire(fix, now))
        in_zone.sort(key=lambda d: d["workerId"])
        in_adjacent.sort(key=lambda d: d["workerId"])
        return {
            "zones": sorted(zones),
            "adjacentZones": sorted(adjacent),
            "inZone": in_zone,
            "inAdjacent": in_adjacent,
            "headcountAtRisk": len(in_zone) + len(in_adjacent),
            "staleFixes": sum(1 for w in in_zone + in_adjacent if w["stale"]),
        }
