"""SIMOPS spatial-temporal conflict detection (spec §5 Pillar 4).

Two permits that are each individually fine become dangerous when they overlap
in TIME and are close in SPACE — e.g. hot work adjacent to a confined-space
entry. This detector takes the set of permits + a zone-adjacency map and finds
the conflicting pairs. Like the risk-engine, it is deterministic and
LLM-independent (P1); each conflict carries lineage to both permits (P3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from verge_schema.core import Permit

# Spatial relation a pair must satisfy to count as a conflict.
SAME_ZONE = "same-zone"
ADJACENT = "adjacent"  # same zone OR a neighbour in the adjacency map
ANY = "any"

# SIMOPS matrix: unordered pair of permit kinds -> (severity, relation, reason).
# Keyed by frozenset so order does not matter.
SIMOPS_MATRIX: dict[frozenset[str], tuple[str, str, str]] = {
    frozenset({"hot-work", "confined-space"}): (
        "critical", ADJACENT, "ignition source adjacent to a confined-space entry"),
    frozenset({"hot-work", "line-breaking"}): (
        "critical", SAME_ZONE, "hot work while a hydrocarbon line is open"),
    frozenset({"confined-space", "line-breaking"}): (
        "critical", SAME_ZONE, "confined-space entry while a line is broken"),
    frozenset({"hot-work"}): (  # two hot-work permits (same kind)
        "warning", SAME_ZONE, "concurrent hot work — cumulative ignition risk"),
    frozenset({"hot-work", "loto"}): (
        "warning", SAME_ZONE, "hot work alongside lockout/tagout activity"),
}

SEVERITY_CONFIDENCE = {"info": 0.4, "warning": 0.65, "critical": 0.8}

AdjacencyMap = dict[str, set[str]]


@dataclass
class PermitConflict:
    permit_a: Permit
    permit_b: Permit
    severity: str
    reason: str
    zones: list[str] = field(default_factory=list)

    @property
    def kinds(self) -> frozenset[str]:
        return frozenset({self.permit_a.kind, self.permit_b.kind})


def _overlaps(a: Permit, b: Permit) -> bool:
    return a.valid_from < b.valid_to and b.valid_from < a.valid_to


def _spatially_related(a: Permit, b: Permit, relation: str, adjacency: AdjacencyMap) -> bool:
    if relation == ANY:
        return True
    if a.zone_id == b.zone_id:
        return True
    if relation == ADJACENT:
        return b.zone_id in adjacency.get(a.zone_id, set()) or a.zone_id in adjacency.get(
            b.zone_id, set()
        )
    return False  # SAME_ZONE and zones differ


def detect_conflicts(
    permits: list[Permit], *, adjacency: AdjacencyMap | None = None, now: datetime | None = None
) -> list[PermitConflict]:
    """Find SIMOPS conflicts among open, time-overlapping, spatially-related permits."""
    adjacency = adjacency or {}
    active = [
        p for p in permits
        if p.status == "open" and (now is None or p.valid_from <= now <= p.valid_to)
    ]
    conflicts: list[PermitConflict] = []
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            if not _overlaps(a, b):
                continue
            rule = SIMOPS_MATRIX.get(frozenset({a.kind, b.kind}))
            if rule is None:
                continue
            severity, relation, reason = rule
            if not _spatially_related(a, b, relation, adjacency):
                continue
            conflicts.append(PermitConflict(
                permit_a=a, permit_b=b, severity=severity, reason=reason,
                zones=sorted({a.zone_id, b.zone_id}),
            ))
    return conflicts
