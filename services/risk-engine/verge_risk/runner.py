"""Streaming runner: turn a live canonical event stream into findings.

This is the service loop behind the demo's live path
(sims -> edge-gateway -> Redpanda -> risk-engine -> api -> console). It is
transport-agnostic: `run_stream` consumes any iterable of canonical event dicts,
so it is unit-testable in-process (feed it sims output or a replay) and also
drives a real Redpanda consumer (`consume_redpanda`, confluent imported lazily).

State is a rolling window per sensor plus active permits and changeover windows;
on each reading the engine re-evaluates and *new* qualifying findings are emitted
once (deduped by zone+title) to a sink.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from datetime import datetime

from verge_schema.core import Permit, Reading, Sensor
from verge_schema.findings import RiskFinding

from .context import RiskContext
from .rules import Rule

DEFAULT_THRESHOLDS = {"gas-lel": 100.0, "gas-co": 50.0}
WINDOW = 12  # readings per sensor (~6 min at 30s cadence)


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


class StreamState:
    """Accumulates the live stream into the snapshot the engine evaluates."""

    def __init__(self, thresholds: dict[str, float] | None = None, window: int = WINDOW) -> None:
        self.thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
        self.window = window
        self.sensors: dict[str, Sensor] = {}
        self.readings: dict[str, deque[Reading]] = {}
        self.permits: list[Permit] = []
        self.changeovers: list[tuple[datetime, datetime, str]] = []
        self._pending: dict[str, datetime] = {}
        self.now: datetime | None = None

    def ingest(self, e: dict) -> str:
        ts = _dt(e["ts"])
        self.now = ts if self.now is None else max(self.now, ts)
        kind = e["type"]
        if kind == "reading":
            sid = e["sensorId"]
            if sid not in self.sensors:
                self.sensors[sid] = Sensor(
                    sensor_id=sid, kind=e["kind"], unit=e.get("unit", ""), zone_id=e["zoneId"],
                    expected_cadence_s=30.0, plausible_min=0.0, plausible_max=1e6,
                )
                self.readings[sid] = deque(maxlen=self.window)
            self.readings[sid].append(Reading(sensor_id=sid, ts=ts, value=e["value"]))
        elif kind == "permit":
            self.permits.append(Permit(
                permit_id=e["permitId"], kind=e["kind"], zone_id=e["zoneId"],
                equipment_id=e.get("equipmentId"),
                valid_from=_dt(e["validFrom"]), valid_to=_dt(e["validTo"]),
            ))
        elif kind == "shift":
            if e["event"] == "changeover-start":
                self._pending[e["zoneId"]] = ts
            elif e["event"] == "changeover-end" and e["zoneId"] in self._pending:
                self.changeovers.append((self._pending.pop(e["zoneId"]), ts, e["zoneId"]))
        return kind

    def in_changeover(self) -> bool:
        return self.now is not None and any(s <= self.now <= e for s, e, _ in self.changeovers)

    def context(self) -> RiskContext:
        windowed = {sid: list(dq) for sid, dq in self.readings.items() if dq}
        return RiskContext(
            now=self.now, sensors=self.sensors, readings=windowed,
            permits=self.permits, thresholds=self.thresholds,
            in_changeover=self.in_changeover(),
        )


def run_stream(
    events: Iterable[dict],
    rules: list[Rule],
    sink: Callable[[RiskFinding], None],
    *,
    thresholds: dict[str, float] | None = None,
    min_confidence: float = 0.8,
) -> int:
    """Drive the engine over a live stream. Emits each qualifying finding once
    (deduped by zone+title). Returns the number emitted."""
    from .engine import evaluate  # local import avoids a cycle at module load

    state = StreamState(thresholds)
    seen: set[tuple[str, str]] = set()
    emitted = 0
    for e in events:
        if state.ingest(e) != "reading":
            continue
        for f in evaluate(state.context(), rules):
            key = (f.zone_id, f.title)
            if key in seen or f.confidence < min_confidence:
                continue
            seen.add(key)
            sink(f)
            emitted += 1
    return emitted


def consume_redpanda(brokers: str, topic: str, rules: list[Rule],
                     sink: Callable[[RiskFinding], None], **kw) -> None:  # pragma: no cover
    """Bridge a Redpanda topic into run_stream. confluent imported lazily."""
    import json

    from confluent_kafka import Consumer

    consumer = Consumer({"bootstrap.servers": brokers, "group.id": "verge-risk-engine",
                         "auto.offset.reset": "latest"})
    consumer.subscribe([topic])

    def gen():
        while True:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            yield json.loads(msg.value())

    try:
        run_stream(gen(), rules, sink, **kw)
    finally:
        consumer.close()
