"""Canonical event envelope (audit §2 contracts, §9 observability).

Every producer boundary should attach stable identity and lineage fields before
events enter the bus so dedupe, tracing, and schema evolution stay deterministic.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from .contracts import ContractRegistry, ContractResult

ENVELOPE_VERSION = "1.0.0"


class ContractViolation(ValueError):
    """Raised when an event fails contract validation at a boundary."""

    def __init__(self, result: ContractResult) -> None:
        self.result = result
        super().__init__("; ".join(result.errors) or "contract violation")


def _site_id(explicit: str | None = None) -> str:
    return explicit or os.environ.get("VERGE_SITE_ID", "demo-site")


def enrich_event(
    event: dict[str, Any],
    *,
    site_id: str | None = None,
    trace_id: str | None = None,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """Attach envelope fields without mutating the caller's dict."""
    out = dict(event)
    out.setdefault("eventId", str(uuid.uuid4()))
    out.setdefault("siteId", _site_id(site_id))
    out.setdefault("schemaVersion", schema_version or out.get("schemaVersion") or ENVELOPE_VERSION)
    out.setdefault("ingestedAt", datetime.now(UTC).isoformat())
    if trace_id:
        out.setdefault("traceId", trace_id)
    return out


def validate_event(
    event: dict[str, Any],
    registry: ContractRegistry | None = None,
) -> ContractResult:
    """Validate core event fields (ignores envelope-only keys)."""
    registry = registry or ContractRegistry()
    core = {k: v for k, v in event.items() if k not in _ENVELOPE_KEYS}
    return registry.validate_event(core)


def validate_and_enrich(
    event: dict[str, Any],
    *,
    site_id: str | None = None,
    trace_id: str | None = None,
    registry: ContractRegistry | None = None,
) -> dict[str, Any]:
    """Validate at a producer boundary; return an enriched canonical event."""
    registry = registry or ContractRegistry()
    result = validate_event(event, registry)
    if not result.valid:
        raise ContractViolation(result)
    core = {k: v for k, v in event.items() if k not in _ENVELOPE_KEYS}
    return enrich_event(
        core,
        site_id=site_id,
        trace_id=trace_id or event.get("traceId"),
        schema_version=result.contract_version,
    )


_ENVELOPE_KEYS = frozenset({
    "eventId", "siteId", "schemaVersion", "ingestedAt", "traceId",
})
