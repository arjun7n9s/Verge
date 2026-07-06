"""Report drafting routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from verge_orchestrator.shift_handover import draft_shift_handover

router = APIRouter(tags=["reports"])


class ShiftHandoverBody(BaseModel):
    actor: str = "maya"
    notes: str
    transcript: str | None = None


@router.post("/reports/shift-handover")
def shift_handover_report(body: ShiftHandoverBody, request: Request) -> dict:
    """Draft shift handover from open findings + operator notes (P8: never auto-submit)."""
    store = request.app.state.store
    llm = request.app.state.llm
    at = datetime.now(UTC)
    findings = store.list_findings(shadow=None)
    draft = draft_shift_handover(
        findings,
        notes=body.notes,
        transcript=body.transcript,
        at=at,
        provider=llm,
    )
    store.audit_append(
        actor=body.actor,
        kind="shift-handover-report",
        payload={
            "openFindings": draft.open_findings,
            "narrativeDegraded": draft.narrative_degraded,
            "submitted": draft.submitted,
            "notesExcerpt": body.notes[:240],
        },
        timestamp=at,
    )
    return {
        "markdown": draft.markdown,
        "openFindings": draft.open_findings,
        "submitted": draft.submitted,
        "narrativeDegraded": draft.narrative_degraded,
    }
