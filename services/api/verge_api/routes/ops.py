"""Plant-IT day-2 operability endpoint (spec §14.6).

Distinct from the safety console: this is what the plant's IT team scrapes and
dashboards. JSON here; Prometheus text at ``/metrics``.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..audit_anchor import anchor_audit_head, verify_anchored_head
from ..backup import snapshot_audit, verify_snapshot
from ..ops import ops_snapshot

router = APIRouter(tags=["ops"])


@router.get("/ops/status")
def ops_status(request: Request) -> dict:
    s = request.app.state
    return ops_snapshot(
        store=s.store,
        readings=s.readings,
        llm=s.llm,
        vision=s.vision,
        version=request.app.version,
        started_at=s.started_at,
        trace_index=getattr(s, "trace_index", None),
    )


@router.get("/ops/backup")
def ops_backup(request: Request) -> dict:
    """Export the audit chain as a verifiable snapshot (§14.6)."""
    return snapshot_audit(request.app.state.store)


@router.post("/ops/backup/verify")
def ops_backup_verify(snapshot: dict) -> dict:
    """Replay a snapshot's hash chain; reject on any mismatch (§14.6).

    Optionally include an out-of-band ``expectedHead`` in the body to anchor
    verification against a trusted head (proof-of-authenticity, not just
    internal consistency)."""
    expected_head = snapshot.get("expectedHead")
    return verify_snapshot(snapshot, expected_head=expected_head)


@router.get("/ops/audit/anchor")
def ops_audit_anchor_status(request: Request) -> dict:
    """Compare live audit head against the last signed anchor in object storage."""
    return verify_anchored_head(request.app.state.store)


@router.post("/ops/audit/anchor")
def ops_audit_anchor(request: Request) -> dict:
    """Sign and upload the current audit head to MinIO (admin)."""
    return anchor_audit_head(request.app.state.store)


@router.get("/ops/trace/{trace_id}")
def ops_trace_lookup(trace_id: str, request: Request) -> dict:
    """Join indexed pipeline spans with audit rows sharing the same trace id."""
    index = getattr(request.app.state, "trace_index", None)
    spans = index.lookup(trace_id) if index is not None else []
    audit = [
        entry
        for entry in request.app.state.store.audit_entries(limit=1000)
        if entry.get("payload", {}).get("traceId") == trace_id
    ]
    return {"traceId": trace_id, "spans": spans, "auditHits": len(audit), "audit": audit[:20]}
