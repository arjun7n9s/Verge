"""Turn SIMOPS conflicts into first-class RiskFindings so they flow through the
same lifecycle, audit, and console as gas-driven findings."""

from __future__ import annotations

from datetime import datetime

from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding

from .conflicts import SEVERITY_CONFIDENCE, PermitConflict


def conflict_to_finding(conflict: PermitConflict, *, at: datetime) -> RiskFinding:
    a, b = conflict.permit_a, conflict.permit_b
    signals = [
        ContributingSignal(kind="permit", ref_id=a.permit_id,
                           summary=f"{a.kind} permit in {a.zone_id}", ts=at),
        ContributingSignal(kind="permit", ref_id=b.permit_id,
                           summary=f"{b.kind} permit in {b.zone_id}", ts=at),
    ]
    zone = conflict.zones[0]
    return RiskFinding(
        finding_id=f"F-SIMOPS-{a.permit_id}-{b.permit_id}",
        created_at=at,
        zone_id=zone,
        title=f"SIMOPS conflict: {a.kind} + {b.kind} ({conflict.reason})",
        state=FindingState.NEW,
        confidence=SEVERITY_CONFIDENCE.get(conflict.severity, 0.6),
        contributing_signals=signals,
        # Permits are not a rate-to-threshold process; lead time is not applicable.
        lead_time_band=LeadTimeBand.UNKNOWN,
        lead_time_basis="SIMOPS conflict (not a rate-based forecast)",
        estimate_quality=EstimateQuality.LOW,
        counterfactual=f"risk drops to LOW if permit {a.permit_id} or {b.permit_id} is closed",
        lineage=[f"permit:{a.permit_id}", f"permit:{b.permit_id}"],
    )


def conflict_findings(
    permits, *, adjacency=None, now: datetime | None = None, at: datetime | None = None
) -> list[RiskFinding]:
    from .conflicts import detect_conflicts

    at = at or now
    return [
        conflict_to_finding(c, at=at)
        for c in detect_conflicts(permits, adjacency=adjacency, now=now)
    ]
