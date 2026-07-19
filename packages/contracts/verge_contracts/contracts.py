"""Data contracts for canonical events (spec §14 Phase 4 — schema registry).

Everything downstream of the edge plane assumes clean canonical events. A data
contract makes that assumption explicit and checkable: each event type
(``reading`` / ``permit`` / ``shift``) has a versioned contract of required and
optional fields with types and constraints. The connector output, an edge
publish, or a replay file can be validated against it before it reaches the
safety core — bad data is rejected at the boundary, not guessed at (P3).

Contracts are versioned so the wire format can evolve without a silent break: a
new field is a new contract version, and the registry keeps the history. Pure
Python, no jsonschema dependency, so it validates on an air-gapped box (P2).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str  # str | number | bool | iso-datetime
    required: bool = True
    choices: tuple[str, ...] | None = None


def _version_key(version: str) -> tuple[int, ...]:
    """Sort key for semver-ish versions so 1.10.0 > 1.9.0 (not lexical)."""
    parts: list[int] = []
    for chunk in version.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break  # stop at the first non-digit (e.g. the '-' in 1.3.0-rc1)
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _type_ok(value: object, type_: str) -> bool:
    if type_ == "str":
        return isinstance(value, str)
    if type_ == "bool":
        return isinstance(value, bool)
    if type_ == "number":
        # A gas reading of NaN/inf must NOT pass: it silently defeats threshold
        # comparisons downstream (nan >= limit is always False). Reject non-finite.
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    if type_ == "list":
        return isinstance(value, list)
    if type_ == "iso-datetime":
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value)
        except ValueError:
            return False
        return True
    return False


@dataclass(frozen=True)
class EventContract:
    event_type: str
    version: str
    fields: tuple[FieldSpec, ...]

    def validate(self, event: dict) -> list[str]:
        """Return a list of human-readable violations ([] means conformant)."""
        errors: list[str] = []
        if event.get("type") != self.event_type:
            errors.append(f"type must be '{self.event_type}', got {event.get('type')!r}")
        for spec in self.fields:
            present = spec.name in event and event[spec.name] is not None
            if not present:
                if spec.required:
                    errors.append(f"missing required field '{spec.name}'")
                continue
            value = event[spec.name]
            if not _type_ok(value, spec.type):
                errors.append(f"field '{spec.name}' must be {spec.type}, got {value!r}")
            elif spec.choices is not None and value not in spec.choices:
                errors.append(f"field '{spec.name}' must be one of {spec.choices}, got {value!r}")
        return errors


# ── the canonical event contracts (v1) ──────────────────────────────────────
READING_V1 = EventContract(
    "reading", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("sensorId", "str"),
        FieldSpec("kind", "str"),
        FieldSpec("unit", "str"),
        FieldSpec("zoneId", "str"),
        FieldSpec("value", "number"),
    ),
)

PERMIT_V1 = EventContract(
    "permit", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("permitId", "str"),
        FieldSpec("kind", "str"),
        FieldSpec("zoneId", "str"),
        FieldSpec("validFrom", "iso-datetime", required=False),
        FieldSpec("validTo", "iso-datetime", required=False),
        FieldSpec("equipmentId", "str", required=False),
    ),
)

SHIFT_V1 = EventContract(
    "shift", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("zoneId", "str"),
        FieldSpec("event", "str",
                  choices=("changeover-start", "changeover-end")),
    ),
)

# Worker positioning uses omlox vocabulary (the open locating standard,
# omlox.com): a *trackable* (badge/tag) is placed in a *zone* by a *location
# provider* (UWB/BLE/GPS/access-control). Verge consumes zone-level presence,
# not coordinates — precise x/y stays in the RTLS hub; the safety layer only
# needs "who is in which zone, how recently".
WORKER_LOCATION_V1 = EventContract(
    "worker-location", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("workerId", "str"),
        FieldSpec("zoneId", "str"),
        FieldSpec("name", "str", required=False),
        FieldSpec("role", "str", required=False),
        FieldSpec("source", "str", required=False),  # omlox location-provider id
    ),
)

VOICE_EVENT_V1 = EventContract(
    "voice-event", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("eventId", "str", required=False),
        FieldSpec("transcript", "str"),
        FieldSpec("zoneId", "str", required=False),
        FieldSpec("hazards", "list", required=False),
        FieldSpec("source", "str", required=False),
    ),
)

VISION_DETECTION_V1 = EventContract(
    "vision-detection", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("zoneId", "str"),
        FieldSpec("cameraId", "str"),
        FieldSpec("label", "str"),
        FieldSpec("confidence", "number", required=False),
        FieldSpec("detectionId", "str", required=False),
        FieldSpec("frameUri", "str", required=False),
    ),
)

MAINTENANCE_V1 = EventContract(
    "maintenance", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("orderId", "str"),
        FieldSpec("equipmentId", "str"),
        FieldSpec("state", "str", required=False),
        FieldSpec("zoneId", "str", required=False),
    ),
)

CAPA_V1 = EventContract(
    "capa", "1.0.0",
    (
        FieldSpec("ts", "iso-datetime"),
        FieldSpec("actionId", "str"),
        FieldSpec("state", "str", required=False),
        FieldSpec("zoneId", "str", required=False),
        FieldSpec("title", "str", required=False),
    ),
)


@dataclass
class ContractResult:
    valid: bool
    event_type: str | None
    contract_version: str | None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "eventType": self.event_type,
            "contractVersion": self.contract_version,
            "errors": self.errors,
        }


class ContractRegistry:
    """Holds the contracts, latest-per-type, and validates events against them."""

    def __init__(self, contracts: Iterable[EventContract] | None = None) -> None:
        self._by_type: dict[str, list[EventContract]] = {}
        for c in contracts or (
            READING_V1,
            PERMIT_V1,
            SHIFT_V1,
            WORKER_LOCATION_V1,
            VOICE_EVENT_V1,
            VISION_DETECTION_V1,
            MAINTENANCE_V1,
            CAPA_V1,
        ):
            self.register(c)

    def register(self, contract: EventContract) -> None:
        self._by_type.setdefault(contract.event_type, []).append(contract)

    def latest(self, event_type: str) -> EventContract | None:
        versions = self._by_type.get(event_type)
        if not versions:
            return None
        return sorted(versions, key=lambda c: _version_key(c.version))[-1]

    def event_types(self) -> list[str]:
        return sorted(self._by_type)

    def validate_event(self, event: dict) -> ContractResult:
        event_type = event.get("type")
        contract = self.latest(event_type) if isinstance(event_type, str) else None
        if contract is None:
            return ContractResult(
                valid=False, event_type=event_type, contract_version=None,
                errors=[f"no contract for event type {event_type!r}"],
            )
        errors = contract.validate(event)
        return ContractResult(
            valid=not errors, event_type=contract.event_type,
            contract_version=contract.version, errors=errors,
        )

    def summary(self) -> dict:
        return {
            "eventTypes": self.event_types(),
            "contracts": {
                t: [c.version for c in sorted(v, key=lambda c: c.version)]
                for t, v in self._by_type.items()
            },
        }


def validate_stream(events: Iterable[dict], registry: ContractRegistry | None = None) -> dict:
    """Validate a batch of events; return counts + the first violations per type."""
    registry = registry or ContractRegistry()
    cap = 50
    total = valid = 0
    violations: list[dict] = []
    for event in events:
        total += 1
        result = registry.validate_event(event)
        if result.valid:
            valid += 1
        elif len(violations) < cap:
            violations.append(result.to_dict())
    invalid = total - valid
    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "violations": violations,
        # Be honest that the violations list is capped (P4): never let a reader
        # believe they have every violation when they don't.
        "violationsShown": len(violations),
        "violationsTruncated": invalid > len(violations),
    }
