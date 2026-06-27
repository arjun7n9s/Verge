"""Plant entities: the nouns the Compound Risk Engine correlates over."""

from datetime import datetime

from pydantic import Field

from ._base import VergeModel
from .enums import DataQuality


class Zone(VergeModel):
    """A geo-fenced area of the plant (PostGIS polygon, WKT here for portability)."""

    zone_id: str
    name: str
    polygon_wkt: str | None = None
    purdue_level: int | None = None


class Equipment(VergeModel):
    equipment_id: str
    name: str
    kind: str  # e.g. coke-oven-battery, raffinate-splitter
    zone_id: str


class Sensor(VergeModel):
    sensor_id: str
    kind: str  # e.g. gas-co, gas-lel, thermal, vibration
    unit: str
    zone_id: str
    equipment_id: str | None = None
    expected_cadence_s: float = 1.0
    plausible_min: float | None = None
    plausible_max: float | None = None
    # Sensor-health plane (spec section 4.7)
    data_quality: DataQuality = DataQuality.LIVE
    last_seen: datetime | None = None


class Reading(VergeModel):
    sensor_id: str
    ts: datetime
    value: float
    # data_quality snapshotted at ingest so historical analysis stays accurate
    data_quality: DataQuality = DataQuality.LIVE


class Permit(VergeModel):
    permit_id: str
    kind: str  # e.g. hot-work, confined-space, loto
    zone_id: str
    equipment_id: str | None = None
    valid_from: datetime
    valid_to: datetime
    status: str = "open"


class MaintenanceOrder(VergeModel):
    order_id: str
    equipment_id: str
    state: str  # e.g. scheduled, in-progress, degraded
    opened_at: datetime


class Worker(VergeModel):
    worker_id: str
    name: str
    role: str


class Shift(VergeModel):
    shift_id: str
    name: str  # e.g. A, B, C / night
    starts_at: datetime
    ends_at: datetime
    changeover_window_min: float = 15.0
    crew: list[str] = Field(default_factory=list)  # worker_ids
