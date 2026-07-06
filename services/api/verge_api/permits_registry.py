"""Active permit registry for the API (demo + live sim feed).

Permits are held in app state — not yet persisted in SqlStore. The sim / edge
gateway can POST updates later; for now we seed Vizag-aligned permits at startup.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from verge_permit import detect_conflicts
from verge_schema.core import Permit
from verge_twin import load_plant


class PermitRegistry:
    def __init__(self) -> None:
        self._permits: list[Permit] = []
        self._adjacency: dict[str, set[str]] = {}

    def seed_demo(self, at: datetime) -> None:
        plant = load_plant()
        self._adjacency = plant.adjacency()
        window = timedelta(hours=4)
        self._permits = [
            Permit(
                permit_id="PW-2025-0142",
                kind="hot-work",
                zone_id="B-04",
                valid_from=at - timedelta(minutes=30),
                valid_to=at + window,
                status="open",
            ),
            Permit(
                permit_id="PW-0140",
                kind="line-breaking",
                zone_id="B-04",
                valid_from=at - timedelta(hours=2),
                valid_to=at + window,
                status="open",
            ),
            Permit(
                permit_id="PW-CS-18",
                kind="confined-space",
                zone_id="B-05",
                valid_from=at - timedelta(minutes=15),
                valid_to=at + window,
                status="open",
            ),
            Permit(
                permit_id="PW-LOTO-09",
                kind="loto",
                zone_id="B-03",
                valid_from=at - timedelta(hours=1),
                valid_to=at + window,
                status="open",
            ),
        ]

    def replace(self, permits: list[Permit]) -> None:
        self._permits = list(permits)

    def list_active(self, *, now: datetime | None = None) -> list[Permit]:
        now = now or datetime.now(UTC)
        return [
            p for p in self._permits
            if p.status == "open" and p.valid_from <= now <= p.valid_to
        ]

    def conflicts(self, *, now: datetime | None = None) -> list[dict]:
        active = self.list_active(now=now)
        rows = detect_conflicts(active, adjacency=self._adjacency, now=now)
        return [
            {
                "permitA": c.permit_a.permit_id,
                "permitB": c.permit_b.permit_id,
                "zones": list(c.zones),
                "reason": c.reason,
                "severity": c.severity,
            }
            for c in rows
        ]

    def as_dicts(self, *, now: datetime | None = None) -> list[dict]:
        return [p.model_dump(by_alias=True, mode="json") for p in self.list_active(now=now)]
