"""Deterministic advisory-brief validator (Phase 2.5 G4).

LLMs propose; this gate decides what may be shown as *recommended*.
Invented twin tags → stripped / demoted. Barriers without evidence → demoted
to open questions. Never raises — always returns a ValidationReport (P4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .twin_catalog import TwinCatalog

# Plant-style tags: B-04, EQ-12, LEL-3A, F-CONV-07, DOC-ABC, VC-HOT-WORK-ish
_TAG_RE = re.compile(
    r"\b(?:"
    r"[A-Z]{1,6}-\d{1,5}[A-Z0-9]*"  # B-04, F-CONV-07, EQ-12A
    r"|[A-Z]{2,}-\d+"                 # PTW-12
    r")\b"
)

# Tokens that look like tags but are domain vocabulary, not twin IDs.
_ALLOWLIST = frozenset({
    "LEL", "PPE", "CO", "H2S", "OISD", "SIMOPS", "PTW", "SOP", "NCR",
    "RCA", "CAPA", "ISO", "PESO", "IMMINENT", "NEAR", "WATCH", "UNKNOWN",
    "LLM", "API", "JSON", "UTC",
})


@dataclass
class ValidationReport:
    ok: bool
    invented_tags: list[str] = field(default_factory=list)
    demoted_barriers: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_wire(self) -> dict:
        return {
            "ok": self.ok,
            "inventedTags": self.invented_tags,
            "demotedBarriers": self.demoted_barriers,
            "notes": self.notes,
        }


def extract_candidate_tags(text: str, catalog: TwinCatalog | None = None) -> set[str]:
    """Extract plant-style IDs from prose.

    Fragments inside a longer *known* id are dropped (``OVEN-1`` inside
    ``EQ-OVEN-1``) so validators don't false-positive on hyphenated names.
    """
    text = text or ""
    found: set[str] = set()
    for m in _TAG_RE.finditer(text):
        tag = m.group(0)
        head = tag.split("-", 1)[0]
        if head in _ALLOWLIST or tag in _ALLOWLIST:
            continue
        found.add(tag)
    if not catalog or not catalog.all_ids():
        return found
    known = catalog.all_ids()
    cleaned: set[str] = set()
    for tag in found:
        if tag in known:
            cleaned.add(tag)
            continue
        # Skip regex fragments that only appear as part of a known id in text.
        if any(kid != tag and tag in kid and kid in text for kid in known):
            continue
        cleaned.add(tag)
    return cleaned


def brief_text_blobs(brief: dict) -> list[str]:
    blobs: list[str] = [str(brief.get("summary") or "")]
    for h in brief.get("hypotheses") or []:
        if isinstance(h, dict):
            blobs.append(str(h.get("cause") or ""))
            blobs.append(str(h.get("supportedBy") or ""))
        else:
            blobs.append(str(h))
    for b in brief.get("recommendedBarriers") or []:
        if isinstance(b, dict):
            blobs.extend([
                str(b.get("action") or ""),
                str(b.get("rationale") or ""),
                str(b.get("supportedBy") or ""),
            ])
        else:
            blobs.append(str(b))
    for r in brief.get("regulatoryRefs") or []:
        if isinstance(r, dict):
            blobs.append(str(r.get("clauseId") or ""))
            blobs.append(str(r.get("relevance") or ""))
    for q in brief.get("openQuestions") or []:
        blobs.append(str(q))
    return blobs


def _barrier_has_evidence(barrier: dict, evidence_tools: set[str], known_refs: set[str]) -> bool:
    """A barrier is citation-backed only if it names a used tool or known ref id.

    A non-empty ``supportedBy`` string alone is not enough — the LLM can invent
    vague labels like ``telemetry`` without tool evidence (G4 harden).
    """
    hay = " ".join(
        str(barrier.get(k) or "")
        for k in ("action", "rationale", "supportedBy", "urgency")
    ).lower()
    if any(t.lower() in hay for t in evidence_tools):
        return True
    return bool(any(ref.lower() in hay for ref in known_refs if len(ref) >= 3))


def validate_brief(
    brief: dict,
    catalog: TwinCatalog,
    *,
    evidence_tools: list[str] | None = None,
    known_refs: list[str] | None = None,
    extra_known: list[str] | None = None,
) -> tuple[dict, ValidationReport]:
    """Return (possibly demoted brief, report). Mutates a shallow copy only."""
    out = {
        "summary": brief.get("summary", ""),
        "hypotheses": list(brief.get("hypotheses") or []),
        "recommendedBarriers": [],
        "regulatoryRefs": list(brief.get("regulatoryRefs") or []),
        "openQuestions": list(brief.get("openQuestions") or []),
    }
    tools = set(evidence_tools or [])
    refs = set(known_refs or [])
    # Finding IDs / permit IDs / clause IDs are not twin topology but are allowed.
    allowed_extra = {str(x) for x in (extra_known or []) if x} | set(refs)

    def _known(tag: str) -> bool:
        return catalog.contains(tag) or tag in allowed_extra

    # Effective catalog for fragment filtering includes extras.
    effective = TwinCatalog(
        zone_ids=catalog.zone_ids | frozenset(allowed_extra),
        equipment_ids=catalog.equipment_ids,
        sensor_ids=catalog.sensor_ids,
        muster_ids=catalog.muster_ids,
    )

    # Invented-tag scan always runs against catalog ∪ extras (empty catalog
    # still rejects tags not in extra_known / known_refs).
    invented: set[str] = set()
    for blob in brief_text_blobs(brief):
        for tag in extract_candidate_tags(blob, effective):
            if not _known(tag):
                invented.add(tag)

    demoted: list[dict] = []
    notes: list[str] = []

    for barrier in brief.get("recommendedBarriers") or []:
        if not isinstance(barrier, dict):
            continue
        barrier_text = " ".join(
            str(barrier.get(k) or "") for k in ("action", "rationale", "supportedBy")
        )
        barrier_tags = extract_candidate_tags(barrier_text, effective)
        bad = {t for t in barrier_tags if not _known(t)}
        if bad:
            demoted.append({**barrier, "reason": f"invented-tags:{sorted(bad)}"})
            out["openQuestions"].append(
                f"Rejected recommendation (unknown twin tag {sorted(bad)}): "
                f"{barrier.get('action', '')}"
            )
            continue
        if not _barrier_has_evidence(barrier, tools, refs):
            demoted.append({**barrier, "reason": "uncited"})
            out["openQuestions"].append(
                f"Demoted uncited recommendation to review: {barrier.get('action', '')}"
            )
            continue
        out["recommendedBarriers"].append(barrier)

    # Surface invented tags found in summary/hypotheses even if barriers were clean.
    if invented:
        notes.append(f"invented-tags-in-brief:{sorted(invented)}")
        out["openQuestions"].append(
            "Brief mentioned twin tags not on the commissioned plant: "
            + ", ".join(sorted(invented))
        )

    report = ValidationReport(
        ok=len(invented) == 0 and len(demoted) == 0,
        invented_tags=sorted(invented),
        demoted_barriers=demoted,
        notes=notes,
    )
    return out, report
