"""Active permit registry — in-memory with optional SQL persistence (M9)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select
from sqlalchemy.engine import Engine
from verge_permit import detect_conflicts
from verge_schema.core import Permit
from verge_twin import load_plant

from . import db


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class PermitRegistry:
    def __init__(self, engine: Engine | None = None) -> None:
        self._permits: dict[str, Permit] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._engine = engine
        if engine is not None:
            self._load_from_db()

    def _load_from_db(self) -> None:
        with self._engine.begin() as conn:  # type: ignore[union-attr]
            rows = conn.execute(select(db.permit)).mappings().all()
        for row in rows:
            permit = Permit(
                permit_id=row["permit_id"],
                kind=row["kind"],
                zone_id=row["zone_id"],
                equipment_id=row["equipment_id"],
                valid_from=_aware(row["valid_from"]),
                valid_to=_aware(row["valid_to"]),
                status=row["status"],
            )
            self._permits[permit.permit_id] = permit

    def _persist(self, permit: Permit) -> None:
        if self._engine is None:
            return
        row = {
            "permit_id": permit.permit_id,
            "kind": permit.kind,
            "zone_id": permit.zone_id,
            "equipment_id": permit.equipment_id,
            "valid_from": permit.valid_from,
            "valid_to": permit.valid_to,
            "status": permit.status,
        }
        with self._engine.begin() as conn:
            conn.execute(delete(db.permit).where(db.permit.c.permit_id == permit.permit_id))
            conn.execute(insert(db.permit).values(**row))

    def _persist_all(self) -> None:
        if self._engine is None:
            return
        with self._engine.begin() as conn:
            conn.execute(delete(db.permit))
            if self._permits:
                conn.execute(
                    insert(db.permit),
                    [
                        {
                            "permit_id": p.permit_id,
                            "kind": p.kind,
                            "zone_id": p.zone_id,
                            "equipment_id": p.equipment_id,
                            "valid_from": p.valid_from,
                            "valid_to": p.valid_to,
                            "status": p.status,
                        }
                        for p in self._permits.values()
                    ],
                )

    def seed_demo(self, at: datetime) -> None:
        if self._permits:
            return
        plant = load_plant()
        self._adjacency = plant.adjacency()
        window = timedelta(hours=4)
        for permit in (
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
        ):
            self._permits[permit.permit_id] = permit
            self._persist(permit)

    def replace(self, permits: list[Permit]) -> None:
        self._permits = {p.permit_id: p for p in permits}
        self._persist_all()

    def upsert(self, permit: Permit) -> None:
        if not self._adjacency:
            self._adjacency = load_plant().adjacency()
        self._permits[permit.permit_id] = permit
        self._persist(permit)

    def upsert_event(self, event: dict) -> None:
        """Upsert from a canonical stream permit event."""
        permit = Permit(
            permit_id=event["permitId"],
            kind=event["kind"],
            zone_id=event["zoneId"],
            equipment_id=event.get("equipmentId"),
            valid_from=datetime.fromisoformat(event["validFrom"]),
            valid_to=datetime.fromisoformat(event["validTo"]),
            status=event.get("status", "open"),
        )
        self.upsert(permit)

    def list_active(self, *, now: datetime | None = None) -> list[Permit]:
        now = now or datetime.now(UTC)
        return [
            p for p in self._permits.values()
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
