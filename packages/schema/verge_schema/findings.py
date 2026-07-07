"""Findings, their lifecycle, feedback, and suppression (spec 4.1, 4.5, 4.6)."""

from datetime import datetime

from pydantic import Field

from ._base import VergeModel
from .enums import (
    EstimateQuality,
    FeedbackVerdict,
    FindingState,
    LeadTimeBand,
    SuppressionStatus,
)


class ContributingSignal(VergeModel):
    """One leg of a compound finding, with its lineage pointer."""

    kind: str  # reading | permit | maintenance | shift | frame
    ref_id: str  # sensor_id / permit_id / ...
    summary: str
    ts: datetime | None = None


class RiskFinding(VergeModel):
    finding_id: str
    created_at: datetime
    zone_id: str
    title: str
    state: FindingState = FindingState.NEW
    owner: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)

    contributing_signals: list[ContributingSignal] = Field(default_factory=list)

    # Lead-time forecast (spec 4.2) -- band, never a point estimate
    lead_time_band: LeadTimeBand = LeadTimeBand.UNKNOWN
    lead_time_basis: str | None = None
    estimate_quality: EstimateQuality = EstimateQuality.LOW

    # Sensor-health degradation (spec 4.7)
    confidence_degraded: bool = False
    confidence_degraded_by: list[str] = Field(default_factory=list)  # sensor_ids

    # Counterfactual lineage (spec section 6)
    counterfactual: str | None = None

    # Lineage: opaque pointers to raw evidence (P3)
    lineage: list[str] = Field(default_factory=list)

    # Shadow mode (spec 14.5): produced while running alongside the existing
    # alarm system; recorded and hash-chained, but not surfaced as a live alert.
    shadow: bool = False

    # Knowledge graph coverage (spec §10.6): True when Neo4j/graph adjacency was
    # unavailable and the finding used sensor-only rules.
    graph_incomplete: bool = False


class FindingEvent(VergeModel):
    """An append-only lifecycle transition. Hash-chains into AuditEntry (spec 4.5)."""

    finding_id: str
    from_state: FindingState | None
    to_state: FindingState
    actor: str
    timestamp: datetime
    reason_code: str | None = None
    reason_text: str | None = None
    hash: str | None = None
    prev_hash: str | None = None


class FindingFeedback(VergeModel):
    """Operator verdict -- labeled ground truth feeding FPR measurement (spec 4.6)."""

    finding_id: str
    actor: str
    timestamp: datetime
    verdict: FeedbackVerdict
    reason_code: str | None = None
    reason_text: str | None = None


class SuppressionSuggestion(VergeModel):
    """Verge proposes a collapse; the operator confirms. Never auto in v3.0 (P8)."""

    suggestion_id: str
    suggested_by: str = "verge"  # verge | operator
    proposed_collapse_of: list[str] = Field(default_factory=list)  # finding_ids
    reason: str
    status: SuppressionStatus = SuppressionStatus.PENDING
    actor_confirmed_by: str | None = None
    timestamp: datetime
