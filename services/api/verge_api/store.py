"""In-memory store (dev / tests / demo). Satisfies StoreProtocol.

Owns findings, the audit hash chain, feedback, and sensor-health counts. The
durable equivalent is SqlStore; both implement StoreProtocol so the API treats
them interchangeably. Every lifecycle transition and feedback event is
hash-chained (P6).
"""

from __future__ import annotations

from datetime import UTC, datetime

from verge_audit import AuditChain
from verge_schema.enums import DataQuality, FeedbackVerdict
from verge_schema.enums import FindingState as S
from verge_schema.findings import FindingFeedback, RiskFinding
from verge_schema.lifecycle import transition

from .outbox import FINDING_TRANSITION, FINDINGS_UPDATED, READING_INGESTED
from .trace import payload_with_trace


def _now() -> datetime:
    return datetime.now(UTC)


class InMemoryStore:
    def __init__(self) -> None:
        self.findings: dict[str, RiskFinding] = {}
        self.feedback: list[FindingFeedback] = []
        self.audit = AuditChain()
        self.sensor_health: dict[DataQuality, int] = {DataQuality.LIVE: 0}
        self._outbox: list[dict] = []

    # ── findings ──────────────────────────────────────────────────────────
    def add_finding(self, f: RiskFinding) -> RiskFinding:
        self.findings[f.finding_id] = f
        self.audit_append(
            actor="risk-engine", kind="finding-created",
            payload=payload_with_trace({"findingId": f.finding_id, "title": f.title}),
            timestamp=f.created_at,
        )
        self._outbox.append({"kind": FINDINGS_UPDATED, "payload": {"findingId": f.finding_id}})
        return f

    def get_finding(self, finding_id: str) -> RiskFinding | None:
        return self.findings.get(finding_id)

    def list_findings(
        self, state: str | None = None, shadow: bool | None = False
    ) -> list[RiskFinding]:
        """`shadow=False` (default) is the operator feed — live findings only.
        `shadow=True` is the shadow-review surface; `shadow=None` returns both."""
        items = list(self.findings.values())
        if state:
            items = [f for f in items if f.state == state]
        if shadow is not None:
            items = [f for f in items if f.shadow == shadow]
        return sorted(items, key=lambda f: f.created_at, reverse=True)

    def shadow_summary(self) -> dict:
        shadow = [f for f in self.findings.values() if f.shadow]
        by_band: dict[str, int] = {}
        for f in shadow:
            by_band[f.lead_time_band] = by_band.get(f.lead_time_band, 0) + 1
        return {"shadow": len(shadow), "byBand": by_band}

    def transition(
        self, finding_id: str, to: S, actor: str,
        reason_code: str | None = None, reason_text: str | None = None,
    ) -> RiskFinding:
        f = self.findings[finding_id]
        ev = transition(finding_id, S(f.state), to, actor=actor, timestamp=_now(),
                        reason_code=reason_code, reason_text=reason_text)
        f.state = to.value
        if to in (S.ASSIGNED, S.IN_PROGRESS) and actor:
            f.owner = actor
        self.audit_append(actor=actor, kind="finding-event",
                          payload=payload_with_trace(ev.model_dump(by_alias=True, mode="json")),
                          timestamp=ev.timestamp)
        self._outbox.append({
            "kind": FINDING_TRANSITION,
            "payload": {"findingId": finding_id, "to": to.value},
        })
        return f

    # ── feedback (spec §4.6) ──────────────────────────────────────────────
    def add_feedback(self, finding_id: str, actor: str, verdict: FeedbackVerdict,
                     reason_code: str | None = None) -> FindingFeedback:
        fb = FindingFeedback(finding_id=finding_id, actor=actor, timestamp=_now(),
                             verdict=verdict, reason_code=reason_code)
        self.feedback.append(fb)
        self.audit_append(actor=actor, kind="feedback",
                          payload=fb.model_dump(by_alias=True, mode="json"),
                          timestamp=fb.timestamp)
        return fb

    def fpr(self) -> float | None:
        if not self.feedback:
            return None
        fa = sum(1 for f in self.feedback if f.verdict == FeedbackVerdict.FALSE_ALARM.value)
        return round(fa / len(self.feedback), 3)

    # ── sensor health (spec §4.7) ─────────────────────────────────────────
    def get_sensor_health(self) -> dict[DataQuality, int]:
        return dict(self.sensor_health)

    def set_sensor_health(self, counts: dict[DataQuality, int]) -> None:
        self.sensor_health = dict(counts)

    # ── audit (P6) ────────────────────────────────────────────────────────
    def audit_append(self, actor: str, kind: str, payload: dict, timestamp: datetime) -> dict:
        return self.audit.append(
            actor=actor, kind=kind, payload=payload, timestamp=timestamp
        ).to_dict()

    def audit_entries(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in list(self.audit)][-limit:]

    def audit_head(self) -> str:
        return self.audit.head

    def audit_len(self) -> int:
        return len(self.audit)

    def audit_verify(self) -> bool:
        try:
            self.audit.verify()
            return True
        except Exception:
            return False

    def outbox_pending(self) -> int:
        return len(self._outbox)

    def drain_outbox(self, publish, *, limit: int = 100) -> int:
        batch = self._outbox[:limit]
        for row in batch:
            publish(row["kind"], row["payload"])
        self._outbox = self._outbox[len(batch):]
        return len(batch)

    def enqueue_reading(self, event: dict, *, skip_redpanda: bool = False) -> None:
        self._outbox.append({
            "kind": READING_INGESTED,
            "payload": {"event": event, "skipRedpanda": skip_redpanda},
        })


# Back-compat alias: `Store` is the in-memory implementation.
Store = InMemoryStore
