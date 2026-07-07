"""Operator-gated alert dispatch (spec §4.4, P8).

Drafting happens in the response flow; this is the *Approve → deliver* action.
It refuses without an approver, delivers across the configured channels (external
ones degrade cleanly with no provider), and hash-chains the delivery receipt.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from verge_orchestrator import dispatch_alert, draft_alert, phrase_for

router = APIRouter(tags=["alerts"])


class DispatchBody(BaseModel):
    approvedBy: str | None = None
    channels: list[str] | None = None
    action: str | None = None
    languages: list[str] | None = None


@router.post("/findings/{finding_id}/alert/dispatch")
def dispatch(finding_id: str, body: DispatchBody, request: Request) -> dict:
    store = request.app.state.store
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")

    now = datetime.now(UTC)
    action = (body.action or "").strip()
    phrase = action or phrase_for(finding)
    alert = draft_alert(
        finding, phrase, issued_at=now, channels=body.channels, languages=body.languages
    )
    receipt = dispatch_alert(
        alert, approved_by=body.approvedBy, dispatched_at=now, channels=body.channels
    )
    # Record the dispatch — including a refused, unapproved attempt (P8 evidence).
    # Attribute an unapproved attempt to "anonymous", never to "system": a human
    # tried, and the audit trail must not read as if the platform self-dispatched.
    actor = (body.approvedBy or "").strip() or "anonymous"
    store.audit_append(
        actor=actor, kind="alert-dispatch", payload=receipt.to_dict(), timestamp=now,
    )
    return receipt.to_dict()
