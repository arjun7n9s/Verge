"""Controlled vocabularies for the Verge data model.

These enums are the contract between services. Adding a value is a schema change
and must be reflected in the JS types (`js/index.ts`) and the eval harness.
"""

from enum import Enum


class FindingState(str, Enum):
    """Lifecycle of a finding (spec section 4.5). A finding is a unit of work,
    not a one-shot alert. Every transition is hash-chained as a FindingEvent."""

    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in-progress"
    SNOOZED = "snoozed"
    ESCALATED = "escalated"
    SUPPRESSED_AS_DUPLICATE = "suppressed-as-duplicate"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class DataQuality(str, Enum):
    """Per-reading sensor health (spec section 4.7). Uncertainty starts at the
    sensor, not just the model."""

    LIVE = "live"
    STALE = "stale"
    STUCK_AT_VALUE = "stuck-at-value"
    OUT_OF_RANGE = "out-of-range"
    CLOCK_SKEWED = "clock-skewed"
    MISSING = "missing"


class LeadTimeBand(str, Enum):
    """Lead-time forecast as a band, never a fake-precise point (spec section 4.2)."""

    IMMINENT = "IMMINENT"  # < 15 min
    NEAR = "NEAR"  # 15-45 min
    WATCH = "WATCH"  # > 45 min
    UNKNOWN = "UNKNOWN"  # insufficient signal -- say so


class EstimateQuality(str, Enum):
    """How much to trust the lead-time band (spec section 4.2)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUPPRESSED = "suppressed"  # degraded contributing sensor; show raw trend


class FeedbackVerdict(str, Enum):
    """Operator feedback on a finding -- labeled ground truth for FPR (spec 4.6)."""

    USEFUL = "useful"
    NOT_USEFUL = "not-useful"
    FALSE_ALARM = "false-alarm"


class SuppressionStatus(str, Enum):
    """Suppression is always operator-confirmed, never automatic in v3.0 (P8)."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


# Bands as (low, high) minutes, half-open. None = unbounded.
BAND_BOUNDS_MIN: dict[LeadTimeBand, tuple[float | None, float | None]] = {
    LeadTimeBand.IMMINENT: (0.0, 15.0),
    LeadTimeBand.NEAR: (15.0, 45.0),
    LeadTimeBand.WATCH: (45.0, None),
    LeadTimeBand.UNKNOWN: (None, None),
}
