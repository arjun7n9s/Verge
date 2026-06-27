"""Finding lifecycle state machine (spec §4.5).

A finding is a unit of work, not a one-shot alert. Transitions are constrained;
each one produces a FindingEvent for the audit hash chain. Two states require a
reason code: `snoozed` (defer-with-deadline) and `suppressed-as-duplicate`
(operator-confirmed merge). Suppression is never automatic (P8) — the caller
must be a human actor.
"""

from __future__ import annotations

from datetime import datetime

from .enums import FindingState as S
from .findings import FindingEvent

# Allowed transitions (spec §4.5 diagram).
ALLOWED: dict[S, set[S]] = {
    S.NEW: {S.ACKNOWLEDGED},
    S.ACKNOWLEDGED: {S.ASSIGNED, S.IN_PROGRESS, S.SNOOZED, S.ESCALATED,
                     S.SUPPRESSED_AS_DUPLICATE, S.RESOLVED},
    S.ASSIGNED: {S.IN_PROGRESS, S.SNOOZED, S.ESCALATED, S.RESOLVED},
    S.IN_PROGRESS: {S.SNOOZED, S.ESCALATED, S.SUPPRESSED_AS_DUPLICATE, S.RESOLVED},
    S.SNOOZED: {S.ACKNOWLEDGED, S.IN_PROGRESS},  # auto-reverts to ACKNOWLEDGED at deadline
    S.ESCALATED: {S.ACKNOWLEDGED, S.IN_PROGRESS, S.RESOLVED},
    S.SUPPRESSED_AS_DUPLICATE: {S.REOPENED},
    S.RESOLVED: {S.CLOSED, S.REOPENED},
    S.CLOSED: {S.REOPENED},
    S.REOPENED: {S.ACKNOWLEDGED, S.IN_PROGRESS},
}

REASON_REQUIRED: set[S] = {S.SNOOZED, S.SUPPRESSED_AS_DUPLICATE, S.ESCALATED}


class IllegalTransition(Exception):
    pass


def can_transition(frm: S, to: S) -> bool:
    return to in ALLOWED.get(frm, set())


def transition(
    finding_id: str,
    frm: S,
    to: S,
    *,
    actor: str,
    timestamp: datetime,
    reason_code: str | None = None,
    reason_text: str | None = None,
) -> FindingEvent:
    """Validate and produce the FindingEvent for an audit append. Raises on an
    illegal transition or a missing required reason code."""
    if not can_transition(frm, to):
        raise IllegalTransition(f"{frm.value} -> {to.value} is not allowed")
    if to in REASON_REQUIRED and not reason_code:
        raise IllegalTransition(f"transition to {to.value} requires a reason_code")
    return FindingEvent(
        finding_id=finding_id,
        from_state=frm,
        to_state=to,
        actor=actor,
        timestamp=timestamp,
        reason_code=reason_code,
        reason_text=reason_text,
    )


def is_terminal(state: S) -> bool:
    # closed can still be reopened, so nothing is truly terminal; closed is "done for now"
    return state is S.CLOSED
