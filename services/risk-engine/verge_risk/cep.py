"""Sliding-window CEP patterns (Flink/Faust-inspired, spec §6).

Stateful pattern matching over canonical events with explicit ``within`` bounds
so memory stays bounded. Complements the YAML rules DSL for temporal joins
(gas + permit + shift in one window).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


@dataclass
class _Event:
    ts: datetime
    event: dict


@dataclass
class CepState:
    """Per-zone rolling event windows keyed by pattern family."""

    window_min: float = 5.0
    max_events: int = 500
    by_zone: dict[str, deque[_Event]] = field(default_factory=lambda: defaultdict(deque))

    def ingest(self, event: dict) -> None:
        zone = event.get("zoneId", "unknown")
        ts = _dt(event["ts"])
        buf = self.by_zone[zone]
        buf.append(_Event(ts=ts, event=event))
        cutoff = ts - timedelta(minutes=self.window_min)
        while buf and buf[0].ts < cutoff:
            buf.popleft()
        while len(buf) > self.max_events:
            buf.popleft()

    def events(self, zone_id: str) -> list[dict]:
        return [e.event for e in self.by_zone.get(zone_id, [])]


def _gas_rising(events: list[dict], *, min_sensors: int = 2) -> list[ContributingSignal] | None:
    """Two+ gas readings rising within the window (B2-style temporal AND)."""
    by_sensor: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for e in events:
        if e.get("type") != "reading" or not str(e.get("kind", "")).startswith("gas"):
            continue
        by_sensor[e["sensorId"]].append((_dt(e["ts"]), float(e["value"])))
    rising: list[ContributingSignal] = []
    for sid, pts in by_sensor.items():
        if len(pts) < 2:
            continue
        pts.sort(key=lambda x: x[0])
        slope = (pts[-1][1] - pts[0][1]) / max(
            (pts[-1][0] - pts[0][0]).total_seconds() / 60.0, 0.01
        )
        if slope > 0.5:
            rising.append(ContributingSignal(
                kind="reading",
                ref_id=sid,
                summary=f"{pts[-1][1]:.1f} rising ({slope:.1f}/min)",
                ts=pts[-1][0],
            ))
    if len(rising) >= min_sensors:
        return rising
    return None


def evaluate_cep(
    state: CepState,
    event: dict,
    *,
    now: datetime | None = None,
) -> list[RiskFinding]:
    """Run CEP patterns after ingesting ``event``; returns new pattern findings."""
    state.ingest(event)
    zone = event.get("zoneId", "unknown")
    now = now or _dt(event["ts"])
    events = state.events(zone)
    findings: list[RiskFinding] = []

    signals = _gas_rising(events)
    if signals:
        findings.append(RiskFinding(
            finding_id=f"F-CEP-{now:%Y%m%dT%H%M%S}",
            created_at=now,
            zone_id=zone,
            title="CEP: multi-sensor gas convergence",
            state=FindingState.NEW,
            confidence=0.88,
            contributing_signals=signals,
            lead_time_band=LeadTimeBand.NEAR,
            lead_time_basis="cep-window",
            estimate_quality=EstimateQuality.MEDIUM,
            lineage=[f"{s.kind}:{s.ref_id}" for s in signals],
            counterfactual="risk drops if gas sensors stabilize below rise threshold",
        ))

    permit_active = any(e.get("type") == "permit" for e in events)
    shift_active = any(
        e.get("type") == "shift" and e.get("event") == "changeover-start" for e in events
    )
    if permit_active and shift_active and signals:
        findings[-1].title = "CEP: permit + shift + gas convergence"
        findings[-1].confidence = 0.92

    return findings
