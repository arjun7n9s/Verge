"""Digital permit-to-work + SIMOPS conflict detection (spec §5 Pillar 4)."""

from .conflicts import (
    ADJACENT,
    ANY,
    SAME_ZONE,
    SIMOPS_MATRIX,
    AdjacencyMap,
    PermitConflict,
    detect_conflicts,
)
from .findings import conflict_findings, conflict_to_finding

__all__ = [
    "ADJACENT",
    "ANY",
    "SAME_ZONE",
    "SIMOPS_MATRIX",
    "AdjacencyMap",
    "PermitConflict",
    "conflict_findings",
    "conflict_to_finding",
    "detect_conflicts",
]
__version__ = "0.3.0"
