"""Streaming runner: turn a live canonical event stream into findings.

This is the service loop behind the demo's live path
(sims -> edge-gateway -> Redpanda -> risk-engine -> api -> console). It is
transport-agnostic: `run_stream` consumes any iterable of canonical event dicts,
so it is unit-testable in-process (feed it sims output or a replay) and also
drives a real Redpanda consumer (`consume_redpanda`, confluent imported lazily).

State is a rolling window per sensor plus active permits and changeover windows;
on each reading the engine re-evaluates and *new* qualifying findings are emitted
once (deduped by zone+lineage+source event) to a sink.
"""

from __future__ import annotations

import json
import os
from collections import deque
from collections.abc import Callable, Iterable
from datetime import datetime

from verge_schema.core import MaintenanceOrder, Permit, Reading, Sensor
from verge_schema.events import VisionDetection, VoiceEvent
from verge_schema.findings import RiskFinding

from .context import RiskContext
from .dedupe_store import DedupeStore
from .rules import Rule

DEFAULT_THRESHOLDS = {
    "gas-lel": 100.0,
    "gas-co": 50.0,
    "vibration": 10.0,
}
WINDOW = 12  # readings per sensor (~6 min at 30s cadence)
MAX_PERMITS = 500
MAX_VOICE = 200
MAX_VISION = 200


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
        self.voice_events: list[VoiceEvent] = []
        self.vision_detections: list[VisionDetection] = []
        self.maintenance_orders: list[MaintenanceOrder] = []
        self.worker_zones: dict[str, str] = {}
        self.now: datetime | None = None

    def _prune_permits(self) -> None:
        """Drop expired permits so memory and SIMOPS state stay bounded (audit §2)."""
        if self.now is None:
            return
        self.permits = [
            p for p in self.permits
            if p.valid_from <= self.now <= p.valid_to
        ][-MAX_PERMITS:]

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
            self._prune_permits()
        elif kind == "shift":
            if e["event"] == "changeover-start":
                self._pending[e["zoneId"]] = ts
            elif e["event"] == "changeover-end" and e["zoneId"] in self._pending:
                self.changeovers.append((self._pending.pop(e["zoneId"]), ts, e["zoneId"]))
        elif kind == "voice-event":
            self.voice_events.append(
                VoiceEvent(
                    event_id=e.get("eventId") or f"VE-{ts:%Y%m%dT%H%M%S}",
                    ts=ts,
                    transcript=e.get("transcript", ""),
                    zone_id=e.get("zoneId"),
                    hazards=list(e.get("hazards") or []),
                    equipment_ids=list(e.get("equipmentIds") or []),
                    source=e.get("source", "radio"),
                )
            )
            self.voice_events = self.voice_events[-MAX_VOICE:]
        elif kind == "vision-detection":
            self.vision_detections.append(
                VisionDetection(
                    detection_id=e.get("detectionId") or f"VD-{ts:%Y%m%dT%H%M%S}",
                    ts=ts,
                    camera_id=e.get("cameraId", "cam"),
                    zone_id=e["zoneId"],
                    label=e.get("label", "unknown"),
                    confidence=float(e.get("confidence", 0.5)),
                    frame_uri=e.get("frameUri"),
                )
            )
            self.vision_detections = self.vision_detections[-MAX_VISION:]
        elif kind == "maintenance":
            self.maintenance_orders.append(
                MaintenanceOrder(
                    order_id=e["orderId"],
                    equipment_id=e["equipmentId"],
                    state=e.get("state", "in-progress"),
                    opened_at=ts,
                    zone_id=e.get("zoneId"),
                )
            )
        elif kind == "worker-location":
            self.worker_zones[e["workerId"]] = e["zoneId"]
        return kind

    def in_changeover(self) -> bool:
        return self.now is not None and any(s <= self.now <= e for s, e, _ in self.changeovers)

    def context(self) -> RiskContext:
        self._prune_permits()
        windowed = {sid: list(dq) for sid, dq in self.readings.items() if dq}
        return RiskContext(
            now=self.now, sensors=self.sensors, readings=windowed,
            permits=self.permits, thresholds=self.thresholds,
            in_changeover=self.in_changeover(),
            voice_events=list(self.voice_events),
            vision_detections=list(self.vision_detections),
            maintenance_orders=list(self.maintenance_orders),
            worker_zones=dict(self.worker_zones),
        )


# An extra detector takes the live StreamState and returns findings (e.g. the
# permit SIMOPS detector). Injected by the caller so the runner needs no
# dependency on the permit/twin packages.
Detector = Callable[["StreamState"], list[RiskFinding]]


def run_stream(
    events: Iterable[dict],
    rules: list[Rule],
    sink: Callable[[RiskFinding], None],
    *,
    thresholds: dict[str, float] | None = None,
    detectors: list[Detector] | None = None,
    shadow: bool = False,
    min_confidence: float = 0.8,
    window: int = WINDOW,
    event_hook: Callable[[dict], None] | None = None,
    after_event: Callable[[dict], None] | None = None,
    enable_cep: bool = False,
    enable_ml: bool = False,
    validate_contracts: bool = True,
    dedupe: DedupeStore | None = None,
) -> int:
    """Drive the engine over a live stream. Runs the gas rules plus any injected
    detectors (e.g. SIMOPS), emits each qualifying finding once (deduped by zone
    + lineage + source event id), and tags findings shadow when running alongside
    an existing alarm system (spec §14.5). Returns the number emitted."""
    from .engine import evaluate  # local import avoids a cycle at module load

    dedupe = dedupe if dedupe is not None else DedupeStore.from_env()

    if validate_contracts:
        from verge_contracts.envelope import validate_and_enrich

    detectors = detectors or []
    state = StreamState(thresholds, window=window)
    cep_state = None
    if enable_cep:
        from .cep import CepState, evaluate_cep

        cep_state = CepState()
    emitted = 0
    try:
        for raw in events:
            e = raw
            if validate_contracts:
                try:
                    e = validate_and_enrich(raw, trace_id=raw.get("traceId"))
                except Exception:
                    continue
            kind = state.ingest(e)
            if event_hook is not None:
                event_hook(e)
            # readings and permits both change the risk picture; re-evaluate on either.
            if kind not in ("reading", "permit"):
                if after_event is not None:
                    after_event(e)
                continue
            findings = list(evaluate(state.context(), rules))
            for detect in detectors:
                findings.extend(detect(state))
            if enable_cep and cep_state is not None and kind == "reading":
                findings.extend(evaluate_cep(cep_state, e, now=state.now))
            if enable_ml and kind == "reading":
                from .ml_layer import ml_findings

                findings.extend(ml_findings(state))
            for f in findings:
                if f.confidence < min_confidence:
                    continue
                key = (f.zone_id, tuple(sorted(f.lineage)))
                if dedupe.seen(key):
                    continue
                dedupe.remember(key)
                if shadow:
                    f.shadow = True
                sink(f)
                emitted += 1
            if after_event is not None:
                after_event(e)
    finally:
        dedupe.save()
    return emitted


def consume_redpanda(brokers: str, topic: str, rules: list[Rule],
                     sink: Callable[[RiskFinding], None], **kw) -> None:  # pragma: no cover
    """Bridge a Redpanda topic into run_stream with explicit offset commits."""

    from confluent_kafka import Consumer, Producer
    from verge_contracts.trace import TRACE_HEADER

    group = os.environ.get("VERGE_RISK_GROUP", "verge-risk-engine")
    offset_reset = os.environ.get("VERGE_KAFKA_OFFSET_RESET", "latest")
    dlq_topic = os.environ.get("VERGE_EVENTS_DLQ", "verge.events.dlq")

    consumer = Consumer({
        "bootstrap.servers": brokers,
        "group.id": group,
        "auto.offset.reset": offset_reset,
        "enable.auto.commit": False,
    })
    consumer.subscribe([topic])
    producer = Producer({"bootstrap.servers": brokers})
    pending_msg = {"msg": None}

    def _trace_from_message(msg) -> str | None:
        for key, value in msg.headers() or []:
            name = key.decode() if isinstance(key, bytes) else key
            if name != TRACE_HEADER:
                continue
            if isinstance(value, bytes):
                return value.decode()
            return str(value)
        return None

    def gen():
        while True:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            pending_msg["msg"] = msg
            try:
                raw = json.loads(msg.value())
                trace_id = raw.get("traceId") or _trace_from_message(msg)
                if trace_id and "traceId" not in raw:
                    raw = {**raw, "traceId": trace_id}
                yield raw
            except json.JSONDecodeError:
                producer.produce(dlq_topic, msg.value(), key=msg.key())
                producer.poll(0)
                consumer.commit(message=msg, asynchronous=False)
                pending_msg["msg"] = None

    def after_event(_e: dict) -> None:
        msg = pending_msg["msg"]
        if msg is not None:
            consumer.commit(message=msg, asynchronous=False)
            pending_msg["msg"] = None

    try:
        run_stream(gen(), rules, sink, after_event=after_event, **kw)
    finally:
        consumer.close()
