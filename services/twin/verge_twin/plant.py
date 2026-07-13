"""Plant digital twin (spec §5 Pillar 3) — the shared spatial substrate.

A PlantModel is the per-site configuration loaded at commissioning (spec §14.5):
zones and their adjacency, equipment, and sensors with their thresholds and
cadence. It is what lets the live engine resolve thresholds and lets the permit
SIMOPS detector know which zones are adjacent. Plain dataclasses + YAML so a
plant is configured, not coded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PLANTS_DIR = Path(__file__).parent / "plants"
DEMO_PLANT = PLANTS_DIR / "vizag-coke-oven.yaml"


@dataclass(frozen=True)
class ZoneNode:
    zone_id: str
    name: str
    adjacent: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SensorNode:
    sensor_id: str
    kind: str
    unit: str
    zone_id: str
    threshold: float | None = None
    cadence_s: float = 30.0


@dataclass(frozen=True)
class EquipmentNode:
    equipment_id: str
    name: str
    kind: str
    zone_id: str


@dataclass(frozen=True)
class MusterPoint:
    """A designated assembly point, anchored to the zone it sits in/beside.

    Safety-by-location is relative: a muster point is only usable when its
    anchor zone is not itself affected — the emergency router checks that.
    """

    muster_id: str
    name: str
    zone_id: str


@dataclass
class PlantModel:
    name: str
    zones: dict[str, ZoneNode] = field(default_factory=dict)
    sensors: dict[str, SensorNode] = field(default_factory=dict)
    equipment: dict[str, EquipmentNode] = field(default_factory=dict)
    muster_points: dict[str, MusterPoint] = field(default_factory=dict)

    def adjacency(self) -> dict[str, set[str]]:
        """zone -> set of neighbouring zones (symmetric, for SIMOPS detection)."""
        adj: dict[str, set[str]] = {z: set(n.adjacent) for z, n in self.zones.items()}
        for z, neighbours in list(adj.items()):
            for n in neighbours:
                adj.setdefault(n, set()).add(z)  # ensure symmetry
        return adj

    def thresholds_by_kind(self) -> dict[str, float]:
        """kind -> threshold (first sensor of each kind that declares one).
        Matches today's kind-keyed engine; see thresholds_by_sensor for per-sensor."""
        out: dict[str, float] = {}
        for s in self.sensors.values():
            if s.threshold is not None and s.kind not in out:
                out[s.kind] = s.threshold
        return out

    def thresholds_by_sensor(self) -> dict[str, float]:
        return {s.sensor_id: s.threshold for s in self.sensors.values() if s.threshold is not None}

    def sensors_in_zone(self, zone_id: str) -> list[SensorNode]:
        return [s for s in self.sensors.values() if s.zone_id == zone_id]


def load_plant(path: str | Path = DEMO_PLANT) -> PlantModel:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    zones = {
        z["id"]: ZoneNode(z["id"], z.get("name", z["id"]), frozenset(z.get("adjacent", [])))
        for z in doc.get("zones", [])
    }
    sensors = {
        s["id"]: SensorNode(
            s["id"], s["kind"], s.get("unit", ""), s["zone"],
            s.get("threshold"), float(s.get("cadenceS", 30.0)),
        )
        for s in doc.get("sensors", [])
    }
    equipment = {
        e["id"]: EquipmentNode(e["id"], e.get("name", e["id"]), e.get("kind", ""), e["zone"])
        for e in doc.get("equipment", [])
    }
    muster_points = {
        m["id"]: MusterPoint(m["id"], m.get("name", m["id"]), m["zone"])
        for m in doc.get("musterPoints", [])
    }
    return PlantModel(
        name=doc["name"], zones=zones, sensors=sensors,
        equipment=equipment, muster_points=muster_points,
    )
