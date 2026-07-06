"""Shift handover report drafting (Dex D6).

Facts come from the store; narrative from LLM when available, else template.
Never auto-submitted (P8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from verge_llm import LLMProvider, Message, NullProvider
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding

_TERMINAL = {S.CLOSED, S.RESOLVED, S.SUPPRESSED_AS_DUPLICATE}
_OPEN = {
    S.NEW, S.ACKNOWLEDGED, S.ASSIGNED, S.IN_PROGRESS,
    S.SNOOZED, S.ESCALATED, S.REOPENED,
}


@dataclass
class ShiftHandoverDraft:
    markdown: str
    open_findings: list[str] = field(default_factory=list)
    submitted: bool = False
    narrative_degraded: bool = False


def _facts(findings: list[RiskFinding], notes: str, transcript: str | None, at: datetime) -> str:
    lines = [
        f"**Handover drafted at** {at.isoformat()}",
        f"**Operator notes** {notes.strip()}",
    ]
    if transcript:
        lines.append(f"**Voice transcript** {transcript.strip()}")
    lines.append(f"**Open findings ({len(findings)})**")
    for f in findings:
        lines.append(
            f"- {f.finding_id} · {f.zone_id} · {f.title} · band {f.lead_time_band} · {f.state}"
        )
    if not findings:
        lines.append("- (none)")
    return "\n".join(lines)


def draft_shift_handover(
    findings: list[RiskFinding],
    *,
    notes: str,
    transcript: str | None = None,
    at: datetime,
    provider: LLMProvider | None = None,
) -> ShiftHandoverDraft:
    provider = provider or NullProvider()
    open_items = [f for f in findings if not f.shadow and S(f.state) in _OPEN]
    facts = _facts(open_items, notes, transcript, at)
    open_ids = [f.finding_id for f in open_items]

    prompt = [
        Message(
            role="system",
            content="You draft concise shift handover summaries for industrial safety operators. "
            "Use only the facts provided.",
        ),
        Message(role="user", content=f"Draft a shift handover summary (4-6 sentences):\n{facts}"),
    ]
    completion = provider.complete(prompt, max_tokens=350)

    if completion.degraded or not completion.text.strip():
        narrative = (
            "Automated shift handover summary (template fallback — LLM narrative unavailable). "
            "Review open findings and operator notes below before sign-off."
        )
        degraded = True
    else:
        narrative = completion.text.strip()
        degraded = False

    markdown = (
        "# SHIFT HANDOVER — operator review required, NOT submitted\n\n"
        f"{narrative}\n\n---\n\n{facts}\n"
    )
    return ShiftHandoverDraft(
        markdown=markdown,
        open_findings=open_ids,
        submitted=False,
        narrative_degraded=degraded,
    )
