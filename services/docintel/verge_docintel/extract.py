"""Deterministic entity extraction from industrial text (LLM-free)."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from verge_schema.documents import EntityKind, EntityMention

# Equipment-like tags common in Indian heavy industry / P&IDs
_EQUIPMENT = re.compile(
    r"\b(?:P|PUMP|T|TK|V|XV|FV|PIC|LIC|LEL|CO|H2S|O2|FI|TI|PI)-?\d{1,4}[A-Z]?\b",
    re.IGNORECASE,
)
_ZONE = re.compile(r"\b(?:ZONE\s*)?([A-Z]{1,3}-\d{1,3})\b")
_CLAUSE = re.compile(r"\b(?:OISD(?:-STD)?|FACTORY\s*ACT|PESO|DGMS)[- ]?\d+[A-Z0-9.-]*\b", re.I)
_PERMIT = re.compile(r"\b(?:PW|PTW|LOTO)[- ]?\d{2,6}\b", re.I)


def _eid(kind: str, raw: str, doc_id: str) -> str:
    digest = hashlib.sha1(f"{doc_id}:{kind}:{raw}".encode()).hexdigest()[:10]
    return f"ent-{digest}"


def extract_entities(text: str, *, document_id: str) -> list[EntityMention]:
    found: list[EntityMention] = []
    seen: set[str] = set()

    def add(kind: EntityKind, raw: str, confidence: float, normalized: str | None = None) -> None:
        key = f"{kind}:{raw.upper()}"
        if key in seen:
            return
        seen.add(key)
        found.append(
            EntityMention(
                entity_id=_eid(kind.value, raw, document_id),
                document_id=document_id,
                kind=kind,
                raw=raw,
                normalized=normalized or raw.upper(),
                confidence=confidence,
            )
        )

    for m in _EQUIPMENT.finditer(text):
        add(EntityKind.EQUIPMENT, m.group(0), 0.8)
    for m in _ZONE.finditer(text):
        add(EntityKind.ZONE, m.group(1), 0.75)
    for m in _CLAUSE.finditer(text):
        add(EntityKind.CLAUSE, m.group(0), 0.7)
    for m in _PERMIT.finditer(text):
        add(EntityKind.PERMIT, m.group(0), 0.75)

    _ = datetime.now(UTC)  # reserved for future temporal entities
    return found
