"""The Finding Investigator agent (spec §4.4 advisory plane).

When a compound finding fires, the investigator autonomously works the same
sources a good safety engineer would — live telemetry, active permits, zone
adjacency and equipment, organizational memory of similar incidents, and the
regulatory clause library — and returns a *cited* brief: every claim traces to
a tool call that is included in the response.

Two hard rules:
- Read-only. The agent has no actuating tools; escalation stays operator-gated.
- Degrades to facts. With no LLM (air-gap, outage), the same tools are called
  directly and composed into a deterministic fact sheet — same shape, honest
  ``degraded: true``, zero fabrication (P4).
"""

from __future__ import annotations

import json

from verge_llm import LLMProvider

from .loop import AgentResult, run_tool_loop
from .tools import ToolRegistry

SYSTEM_PROMPT = """You are the Verge finding investigator — a process-safety \
analysis agent for an Indian heavy-industry plant. A compound risk finding has \
fired. Investigate it using ONLY the provided tools; never invent readings, \
permits, or history. Cite which tool result supports each statement.

Return STRICT JSON (no markdown fence) with keys:
  summary            one-paragraph situation assessment
  hypotheses         array of {cause, likelihood: high|medium|low, supportedBy}
  recommendedBarriers array of {action, urgency: immediate|this-shift|planned, rationale}
  regulatoryRefs     array of {clauseId, relevance}
  openQuestions      array of strings — what you could NOT verify with tools

Ground rules: hypotheses must reference tool evidence in supportedBy; \
recommendations follow the hierarchy of controls (eliminate > engineer > \
administrate > PPE); if telemetry is degraded or stale, say so in \
openQuestions rather than guessing."""

BRIEF_KEYS = ("summary", "hypotheses", "recommendedBarriers", "regulatoryRefs", "openQuestions")

# Tools every investigation starts from in the degraded (LLM-free) path.
_FACT_TOOLS = (
    ("get_finding", lambda fid: {"findingId": fid}),
    ("get_zone_context", None),
    ("get_recent_telemetry", lambda fid: {"findingId": fid}),
    ("get_active_permits", None),
    ("search_incident_memory", None),
    ("get_compliance_clauses", None),
)


def _parse_brief(text: str) -> dict | None:
    """Parse the model's JSON brief; tolerate a stray code fence."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0] if "```" in raw else raw
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or "summary" not in data:
        return None
    return {k: data.get(k, [] if k != "summary" else "") for k in BRIEF_KEYS}


def _degraded_brief(finding_id: str, zone_id: str, tools: ToolRegistry) -> tuple[dict, list]:
    """LLM-free fact sheet: call the core tools directly, compose honestly."""
    steps = []
    facts: dict[str, object] = {}
    calls = {
        "get_finding": {"finding_id": finding_id},
        "get_zone_context": {"zone_id": zone_id},
        "get_recent_telemetry": {"finding_id": finding_id},
        "get_active_permits": {"zone_id": zone_id},
        "search_incident_memory": {"query": f"incidents similar to finding in zone {zone_id}"},
        "get_compliance_clauses": {"zone_id": zone_id},
    }
    for name, args in calls.items():
        if tools.get(name) is None:
            continue
        result = tools.execute(name, args)
        steps.append({"tool": name, "arguments": args, "result": result})
        try:
            facts[name] = json.loads(result)
        except (ValueError, TypeError):
            facts[name] = result

    permits = facts.get("get_active_permits") or []
    permit_note = (
        f"{len(permits)} active permit(s) in/near the zone"
        if isinstance(permits, list)
        else "permit state unavailable"
    )
    brief = {
        "summary": (
            f"Deterministic fact sheet for {finding_id} (no LLM available — "
            f"facts only, no synthesis). Zone {zone_id}: {permit_note}. "
            "Telemetry, adjacency, memory, and clause data attached as evidence steps."
        ),
        "hypotheses": [],
        "recommendedBarriers": [],
        "regulatoryRefs": [
            {"clauseId": c.get("clauseId", ""), "relevance": c.get("title", "")}
            for c in (facts.get("get_compliance_clauses") or [])
            if isinstance(c, dict)
        ][:5],
        "openQuestions": [
            "LLM synthesis unavailable — hypotheses and barrier recommendations "
            "require the intelligence plane or a safety engineer's review."
        ],
    }
    return brief, steps


def investigate(
    provider: LLMProvider,
    *,
    finding_id: str,
    zone_id: str,
    title: str,
    tools: ToolRegistry,
    model: str | None = None,
    max_steps: int = 6,
) -> dict:
    """Run the investigation; always returns a wire-shaped brief."""
    user = (
        f"Investigate finding {finding_id} in zone {zone_id}: \"{title}\".\n"
        "Work the tools, then produce the JSON brief."
    )
    result: AgentResult = run_tool_loop(
        provider, system=SYSTEM_PROMPT, user=user, tools=tools,
        model=model, max_steps=max_steps,
    )

    if result.degraded:
        brief, steps = _degraded_brief(finding_id, zone_id, tools)
        return {
            "findingId": finding_id,
            "brief": brief,
            "evidence": steps,
            "degraded": True,
            "reason": result.reason,
            "model": result.model,
        }

    brief = _parse_brief(result.answer)
    if brief is None:
        # The model answered but not in-contract: return its text honestly
        # flagged rather than pretending it parsed (P4).
        brief = {
            "summary": result.answer[:2000],
            "hypotheses": [], "recommendedBarriers": [],
            "regulatoryRefs": [], "openQuestions": ["response was not valid JSON"],
        }
    return {
        "findingId": finding_id,
        "brief": brief,
        "evidence": [s.to_wire() for s in result.steps],
        "degraded": False,
        "reason": None,
        "model": result.model,
    }
