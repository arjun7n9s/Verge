"""The connector contract for the integration hub (spec §14 Phase 4).

A connector reads from an external plant system — a historian (OSIsoft PI,
Honeywell PHD), a CMMS (SAP PM, Maximo), a VMS (Milestone, Genetec) — and emits
**canonical Verge events** (the same reading/permit/shift dicts the edge plane
produces), so everything downstream sees one shape regardless of source.

Two rules, shared with the rest of the intelligence layer:

* **Degrade, never fabricate (P4).** A connector with no configuration, no
  network, or no credentials returns ``ConnectorResult(events=[], degraded=True,
  reason=...)`` — never invented readings. Proprietary connectors that need a
  live network default to degraded on the dev/air-gapped box.
* **Unmapped is dropped, not guessed (P3).** A source tag with no mapping to a
  commissioned sensor is skipped and counted, never assigned to a guessed zone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ConnectorResult:
    source: str
    events: list[dict] = field(default_factory=list)
    degraded: bool = False
    reason: str = ""
    skipped: int = 0  # source records that could not be mapped

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "events": self.events,
            "count": len(self.events),
            "degraded": self.degraded,
            "reason": self.reason,
            "skipped": self.skipped,
        }


@runtime_checkable
class Connector(Protocol):
    name: str

    def pull(self, since: str | None = None) -> ConnectorResult:
        """Pull canonical events (optionally only those after ISO ``since``)."""
        ...


def degraded(source: str, reason: str) -> ConnectorResult:
    """Helper for the common 'not configured / unreachable' path."""
    return ConnectorResult(source=source, degraded=True, reason=reason)
