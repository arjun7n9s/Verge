"""Verge canonical data model — the single source of truth across services."""

from .audit import Action, Alert, AuditEntry, EvidencePack
from .core import (
    Equipment,
    MaintenanceOrder,
    Permit,
    Reading,
    Sensor,
    Shift,
    Worker,
    Zone,
)
from .enums import (
    BAND_BOUNDS_MIN,
    DataQuality,
    EstimateQuality,
    FeedbackVerdict,
    FindingState,
    LeadTimeBand,
    SuppressionStatus,
)
from .documents import (
    DocumentAsset,
    DocumentChunk,
    DocumentKind,
    DocumentStatus,
    EntityKind,
    EntityMention,
)
from .findings import (
    ContributingSignal,
    FindingEvent,
    FindingFeedback,
    RiskFinding,
    SuppressionSuggestion,
)

__all__ = [
    "BAND_BOUNDS_MIN",
    "Action",
    "Alert",
    "AuditEntry",
    "ContributingSignal",
    "DataQuality",
    "DocumentAsset",
    "DocumentChunk",
    "DocumentKind",
    "DocumentStatus",
    "EntityKind",
    "EntityMention",
    "Equipment",
    "EstimateQuality",
    "EvidencePack",
    "FeedbackVerdict",
    "FindingEvent",
    "FindingFeedback",
    "FindingState",
    "LeadTimeBand",
    "MaintenanceOrder",
    "Permit",
    "Reading",
    "RiskFinding",
    "Sensor",
    "Shift",
    "SuppressionStatus",
    "SuppressionSuggestion",
    "Worker",
    "Zone",
]

__version__ = "0.3.0"
