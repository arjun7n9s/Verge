"""Durable store (SQLAlchemy). Satisfies StoreProtocol.

Findings/feedback/sensor-health live in the DB and are queried directly.
The audit chain is the subtle part: the DB is the durable record, and an
in-memory AuditChain mirrors it for O(1) head/verify. On startup the chain is
rebuilt from the persisted rows and **re-verified** — so audit integrity holds
across restarts, and a snapshot restore that fails to re-verify is rejected
(spec §10.6, §14.6, P6).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from verge_audit import AuditChain
from verge_schema.enums import DataQuality, FeedbackVerdict
from verge_schema.enums import FindingState as S
from verge_schema.findings import FindingFeedback, RiskFinding
from verge_schema.lifecycle import transition

from . import db
from .outbox import FINDING_TRANSITION, FINDINGS_UPDATED, READING_INGESTED


def _now() -> datetime:
    return datetime.now(UTC)


class SqlStore:
    def __init__(self, url: str = "sqlite:///verge.db") -> None:
        self.engine = db.make_engine(url)
        self._chain = self._load_chain()  # rebuilds + verifies (raises if corrupt)

    # ── audit chain bootstrap ─────────────────────────────────────────────
    def _load_chain(self) -> AuditChain:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(db.audit_entry).order_by(db.audit_entry.c.seq)
            ).mappings().all()
        return AuditChain.from_persisted(
            {
                "entryId": r["entry_id"], "timestamp": r["ts"], "actor": r["actor"],
                "kind": r["kind"], "payload": r["payload"], "prevHash": r["prev_hash"],
                "hash": r["hash"],
            }
            for r in rows
        )

    # ── findings ──────────────────────────────────────────────────────────
    def _upsert_finding(self, conn, f: RiskFinding) -> None:
        values = {
            "finding_id": f.finding_id,
            "zone_id": f.zone_id,
            "state": str(f.state),
            "shadow": bool(f.shadow),
            "created_at": f.created_at,
            "data": f.model_dump(by_alias=True, mode="json"),
        }
        if conn.dialect.name == "postgresql":
            stmt = pg_insert(db.finding).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[db.finding.c.finding_id],
                set_=values,
            )
        else:
            stmt = sqlite_insert(db.finding).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[db.finding.c.finding_id],
                set_=values,
            )
        conn.execute(stmt)

    def _enqueue_outbox(
        self, conn, kind: str, payload: dict, *, at: datetime | None = None,
    ) -> None:
        conn.execute(insert(db.outbox_event).values(
            kind=kind,
            payload=payload,
            created_at=at or _now(),
        ))

    def _persist_audit(self, conn, entry) -> None:
        ts_iso = entry.timestamp.isoformat() if isinstance(entry.timestamp, datetime) \
            else str(entry.timestamp)
        conn.execute(insert(db.audit_entry).values(
            entry_id=entry.entry_id, ts=ts_iso, actor=entry.actor,
            kind=entry.kind, payload=entry.payload, hash=entry.hash,
            prev_hash=entry.prev_hash,
        ))

    def add_finding(self, f: RiskFinding) -> RiskFinding:
        # Finding + audit + outbox in one transaction (audit §4 outbox pattern).
        entry = self._chain.append(
            actor="risk-engine",
            kind="finding-created",
            payload={"findingId": f.finding_id, "title": f.title},
            timestamp=f.created_at,
        )
        try:
            with self.engine.begin() as conn:
                self._upsert_finding(conn, f)
                self._persist_audit(conn, entry)
                self._enqueue_outbox(conn, FINDINGS_UPDATED, {"findingId": f.finding_id})
        except Exception:
            self._chain = self._load_chain()
            raise
        return f

    def get_finding(self, finding_id: str) -> RiskFinding | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(db.finding.c.data).where(db.finding.c.finding_id == finding_id)
            ).scalar_one_or_none()
        return RiskFinding.model_validate(row) if row else None

    def list_findings(
        self, state: str | None = None, shadow: bool | None = False
    ) -> list[RiskFinding]:
        q = select(db.finding.c.data).order_by(db.finding.c.created_at.desc())
        if state:
            q = q.where(db.finding.c.state == state)
        if shadow is not None:
            q = q.where(db.finding.c.shadow == shadow)
        with self.engine.begin() as conn:
            return [RiskFinding.model_validate(r) for r in conn.execute(q).scalars().all()]

    def shadow_summary(self) -> dict:
        with self.engine.begin() as conn:
            total = conn.execute(
                select(func.count()).select_from(db.finding).where(db.finding.c.shadow.is_(True))
            ).scalar_one()
            rows = conn.execute(
                select(db.finding.c.data).where(db.finding.c.shadow.is_(True))
            ).scalars().all()
        by_band: dict[str, int] = {}
        for data in rows:
            band = data.get("leadTimeBand", "UNKNOWN")
            by_band[band] = by_band.get(band, 0) + 1
        return {"shadow": total, "byBand": by_band}

    def transition(
        self, finding_id: str, to: S, actor: str,
        reason_code: str | None = None, reason_text: str | None = None,
    ) -> RiskFinding:
        f = self.get_finding(finding_id)
        if f is None:
            raise KeyError(finding_id)
        ev = transition(finding_id, S(f.state), to, actor=actor, timestamp=_now(),
                        reason_code=reason_code, reason_text=reason_text)
        f.state = to.value
        if to in (S.ASSIGNED, S.IN_PROGRESS) and actor:
            f.owner = actor
        entry = self._chain.append(
            actor=actor,
            kind="finding-event",
            payload=ev.model_dump(by_alias=True, mode="json"),
            timestamp=ev.timestamp,
        )
        try:
            with self.engine.begin() as conn:
                conn.execute(update(db.finding).where(db.finding.c.finding_id == finding_id).values(
                    state=to.value, data=f.model_dump(by_alias=True, mode="json"),
                ))
                self._persist_audit(conn, entry)
                self._enqueue_outbox(
                    conn,
                    FINDING_TRANSITION,
                    {"findingId": finding_id, "to": to.value},
                )
        except Exception:
            self._chain = self._load_chain()
            raise
        return f

    # ── feedback (spec §4.6) ──────────────────────────────────────────────
    def add_feedback(self, finding_id: str, actor: str, verdict: FeedbackVerdict,
                     reason_code: str | None = None) -> FindingFeedback:
        fb = FindingFeedback(finding_id=finding_id, actor=actor, timestamp=_now(),
                             verdict=verdict, reason_code=reason_code)
        with self.engine.begin() as conn:
            conn.execute(insert(db.finding_feedback).values(
                finding_id=finding_id, actor=actor, verdict=str(fb.verdict),
                reason_code=reason_code, timestamp=fb.timestamp,
            ))
        self.audit_append(actor, "feedback", fb.model_dump(by_alias=True, mode="json"),
                          fb.timestamp)
        return fb

    def fpr(self) -> float | None:
        with self.engine.begin() as conn:
            total = conn.execute(select(func.count()).select_from(db.finding_feedback)).scalar_one()
            if not total:
                return None
            fa = conn.execute(
                select(func.count()).select_from(db.finding_feedback)
                .where(db.finding_feedback.c.verdict == FeedbackVerdict.FALSE_ALARM.value)
            ).scalar_one()
        return round(fa / total, 3)

    # ── sensor health (spec §4.7) ─────────────────────────────────────────
    def get_sensor_health(self) -> dict[DataQuality, int]:
        with self.engine.begin() as conn:
            rows = conn.execute(select(db.sensor_health)).mappings().all()
        return {DataQuality(r["quality"]): r["count"] for r in rows}

    def set_sensor_health(self, counts: dict[DataQuality, int]) -> None:
        with self.engine.begin() as conn:
            conn.execute(delete(db.sensor_health))
            if counts:
                conn.execute(insert(db.sensor_health), [
                    {"quality": q.value, "count": n} for q, n in counts.items()
                ])

    # ── audit (P6) ────────────────────────────────────────────────────────
    def audit_append(self, actor: str, kind: str, payload: dict, timestamp: datetime) -> dict:
        entry = self._chain.append(actor=actor, kind=kind, payload=payload, timestamp=timestamp)
        # Store the exact ISO string the hash was computed over (see db.audit_entry.ts).
        ts_iso = entry.timestamp.isoformat() if isinstance(entry.timestamp, datetime) \
            else str(entry.timestamp)
        with self.engine.begin() as conn:
            conn.execute(insert(db.audit_entry).values(
                entry_id=entry.entry_id, ts=ts_iso, actor=entry.actor,
                kind=entry.kind, payload=entry.payload, hash=entry.hash,
                prev_hash=entry.prev_hash,
            ))
        return entry.to_dict()

    def audit_entries(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in list(self._chain)][-limit:]

    def audit_head(self) -> str:
        return self._chain.head

    def audit_len(self) -> int:
        return len(self._chain)

    def audit_verify(self) -> bool:
        try:
            self._load_chain()  # re-read from DB and verify the persisted record
            return True
        except Exception:
            return False

    def outbox_pending(self) -> int:
        with self.engine.begin() as conn:
            return conn.execute(
                select(func.count()).select_from(db.outbox_event)
                .where(db.outbox_event.c.published_at.is_(None))
            ).scalar_one()

    def drain_outbox(self, publish, *, limit: int = 100) -> int:
        """Publish unpublished outbox rows; mark published in the same transaction."""
        now = _now()
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(db.outbox_event)
                .where(db.outbox_event.c.published_at.is_(None))
                .order_by(db.outbox_event.c.id)
                .limit(limit)
            ).mappings().all()
            for row in rows:
                publish(row["kind"], row["payload"])
                conn.execute(
                    update(db.outbox_event)
                    .where(db.outbox_event.c.id == row["id"])
                    .values(published_at=now)
                )
        return len(rows)

    def enqueue_reading(self, event: dict, *, skip_redpanda: bool = False) -> None:
        """Queue a reading-ingested notification (Timescale/buffer already written)."""
        with self.engine.begin() as conn:
            self._enqueue_outbox(
                conn,
                READING_INGESTED,
                {"event": event, "skipRedpanda": skip_redpanda},
            )
