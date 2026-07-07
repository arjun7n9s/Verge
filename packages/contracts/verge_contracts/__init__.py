"""Data contracts + schema registry for canonical events (spec §14 Phase 4).

Versioned, dependency-free validation of reading/permit/shift events so bad data
is rejected at the boundary, not guessed at (P3), and the wire format can evolve
without a silent break.
"""

from .contracts import (
    PERMIT_V1,
    READING_V1,
    SHIFT_V1,
    ContractRegistry,
    ContractResult,
    EventContract,
    FieldSpec,
    validate_stream,
)
from .envelope import (
    ENVELOPE_VERSION,
    ContractViolation,
    enrich_event,
    validate_and_enrich,
    validate_event,
)

__all__ = [
    "PERMIT_V1",
    "READING_V1",
    "SHIFT_V1",
    "ContractRegistry",
    "ContractResult",
    "EventContract",
    "FieldSpec",
    "validate_stream",
    "ENVELOPE_VERSION",
    "ContractViolation",
    "enrich_event",
    "validate_and_enrich",
    "validate_event",
]
__version__ = "0.3.0"
