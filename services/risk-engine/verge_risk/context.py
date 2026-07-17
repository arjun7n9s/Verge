"""The snapshot a rule evaluates against, and per-zone views of it."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from verge_schema.core import MaintenanceOrder, Permit, Reading, Sensor
from verge_schema.events import VisionDetection, VoiceEvent


@dataclass
class RiskContext:
    """Everything the engine needs at one instant. Built from the streams by the
    service; constructed directly in tests and the eval harness."""

    now: datetime
    sensors: dict[str, Sensor]  # sensor_id -> Sensor
    readings: dict[str, list[Reading]]  # sensor_id -> recent window (ascending)
    permits: list[Permit] = field(default_factory=list)  # active permits
    thresholds: dict[str, float] = field(default_factory=dict)  # sensor_kind -> alarm
    in_changeover: bool = False
    voice_events: list[VoiceEvent] = field(default_factory=list)
    vision_detections: list[VisionDetection] = field(default_factory=list)
    maintenance_orders: list[MaintenanceOrder] = field(default_factory=list)
    worker_zones: dict[str, str] = field(default_factory=dict)  # worker_id -> zone_id

    def zone(self, zone_id: str) -> ZoneView:
        return ZoneView(self, zone_id)


@dataclass
class ZoneView:
    ctx: RiskContext
    zone_id: str

    def sensors_of_kind(self, kind: str) -> list[Sensor]:
        return [
            s for s in self.ctx.sensors.values() if s.zone_id == self.zone_id and s.kind == kind
        ]

    def active_permits(self, kind: str | None = None) -> list[Permit]:
        out = []
        for p in self.ctx.permits:
            if p.zone_id != self.zone_id:
                continue
            if kind and p.kind != kind:
                continue
            if p.valid_from <= self.ctx.now <= p.valid_to and p.status == "open":
                out.append(p)
        return out

    def readings_for(self, sensor_id: str) -> list[Reading]:
        return self.ctx.readings.get(sensor_id, [])
