"""Orchestrator: specialists fan-out + merge + validate (no network)."""

from __future__ import annotations

import json

from verge_agents import Tool, ToolRegistry, TwinCatalog, investigate, orchestrate
from verge_llm import Completion, NullProvider


class ScriptedProvider:
    name = "scripted"

    def __init__(self, script: list[Completion]) -> None:
        self._script = list(script)
        self.calls: list[dict] = []

    def complete(self, messages, **kw) -> Completion:
        return self.chat(messages, **kw)

    def chat(self, messages, *, tools=None, model=None, **kw) -> Completion:
        self.calls.append({"messages": messages, "tools": tools})
        return self._script.pop(0)

    def healthy(self) -> bool:
        return True


def _tools() -> ToolRegistry:
    return ToolRegistry([
        Tool("get_finding", "f",
             lambda finding_id="": {
                 "findingId": finding_id or "F-1",
                 "title": "hot work",
                 "leadTimeBand": "NEAR",
                 "lineage": ["LEL-04A"],
                 "zoneId": "B-04",
             },
             {"type": "object", "properties": {"finding_id": {"type": "string"}}}),
        Tool("get_zone_context", "z",
             lambda zone_id="": {
                 "zoneId": zone_id or "B-04",
                 "adjacentZones": ["B-03"],
                 "sensors": [{"sensorId": "LEL-04A"}],
                 "equipment": [{"equipmentId": "EQ-OVEN-1"}],
             },
             {"type": "object", "properties": {"zone_id": {"type": "string"}}}),
        Tool("get_recent_telemetry", "t",
             lambda finding_id="": {"series": []},
             {"type": "object", "properties": {"finding_id": {"type": "string"}}}),
        Tool("get_active_permits", "p",
             lambda zone_id="": [{"permitId": "PTW-1", "zoneId": "B-04"}],
             {"type": "object", "properties": {"zone_id": {"type": "string"}}}),
        Tool("get_equipment_graph", "g",
             lambda zone_id="": {"equipment": []},
             {"type": "object", "properties": {"zone_id": {"type": "string"}}}),
        Tool("search_incident_memory", "m",
             lambda query="": {"answer": "", "citations": [], "degraded": True},
             {"type": "object", "properties": {"query": {"type": "string"}}}),
        Tool("search_plant_docs", "d",
             lambda query="": {
                 "citations": [{"documentId": "DOC-1", "excerpt": "purge before hot work"}],
             },
             {"type": "object", "properties": {"query": {"type": "string"}}}),
        Tool("query_zone_graph", "q",
             lambda zone_id="": {"hops": [{"from": "B-04", "to": "B-03"}]},
             {"type": "object", "properties": {"zone_id": {"type": "string"}}}),
        Tool("get_compliance_clauses", "c",
             lambda zone_id="": [{"clauseId": "VC-HOT-WORK", "title": "Hot work"}],
             {"type": "object", "properties": {"zone_id": {"type": "string"}}}),
    ])


def _catalog() -> TwinCatalog:
    return TwinCatalog(
        zone_ids=frozenset({"B-04", "B-03"}),
        equipment_ids=frozenset({"EQ-OVEN-1"}),
        sensor_ids=frozenset({"LEL-04A"}),
    )


def test_orchestrator_degraded_runs_specialists():
    out = orchestrate(
        NullProvider(),
        finding_id="F-1",
        zone_id="B-04",
        title="hot work",
        tools=_tools(),
        catalog=_catalog(),
        include_multimodal=False,
    )
    assert out["degraded"] is True
    assert out["orchestrator"] == "advisory-v1"
    names = [s["name"] for s in out["specialists"]]
    assert "telemetry" in names and "knowledge" in names and "compliance" in names
    tools_called = {e["tool"] for e in out["evidence"]}
    assert "get_finding" in tools_called
    assert "search_plant_docs" in tools_called
    assert "get_compliance_clauses" in tools_called
    assert out["validation"]["ok"] is True  # fact sheet has no bad barriers


def test_orchestrator_merge_and_strip_invented_tag():
    brief = {
        "summary": "Hot work in B-04.",
        "hypotheses": [{"cause": "purge gap", "likelihood": "high",
                        "supportedBy": "knowledge"}],
        "recommendedBarriers": [
            {
                "action": "Isolate GHOST-77 immediately",
                "urgency": "immediate",
                "rationale": "invented",
                "supportedBy": "get_zone_context",
            },
            {
                "action": "Hold PTW near EQ-OVEN-1",
                "urgency": "immediate",
                "rationale": "SIMOPS",
                "supportedBy": "get_active_permits",
            },
        ],
        "regulatoryRefs": [{"clauseId": "VC-HOT-WORK", "relevance": "hot work"}],
        "openQuestions": [],
    }
    provider = ScriptedProvider([Completion(json.dumps(brief), "m")])
    out = orchestrate(
        provider,
        finding_id="F-1",
        zone_id="B-04",
        title="hot work",
        tools=_tools(),
        catalog=_catalog(),
        include_multimodal=False,
    )
    assert out["degraded"] is False
    assert "GHOST-77" in out["validation"]["inventedTags"]
    actions = [b["action"] for b in out["brief"]["recommendedBarriers"]]
    assert actions == ["Hold PTW near EQ-OVEN-1"]
    assert any("GHOST-77" in q for q in out["brief"]["openQuestions"])


def test_investigate_entrypoint_uses_orchestrator():
    out = investigate(
        NullProvider(),
        finding_id="F-1",
        zone_id="B-04",
        title="t",
        tools=_tools(),
        catalog=_catalog(),
    )
    assert out["orchestrator"] == "advisory-v1"
    assert "specialists" in out


def test_orchestrator_parses_fenced_json_brief():
    brief = {
        "summary": "Hot work in B-04 near rising LEL.",
        "hypotheses": [{"cause": "SIMOPS", "likelihood": "high",
                        "supportedBy": "telemetry"}],
        "recommendedBarriers": [
            {
                "action": "Hold work near EQ-OVEN-1 in B-04",
                "urgency": "immediate",
                "rationale": "atmosphere uncertain",
                "supportedBy": "get_active_permits",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    fenced = "```json\n" + json.dumps(brief) + "\n```\n"
    provider = ScriptedProvider([Completion(fenced, "m")])
    out = orchestrate(
        provider,
        finding_id="F-1",
        zone_id="B-04",
        title="hot work",
        tools=_tools(),
        catalog=_catalog(),
        include_multimodal=False,
    )
    assert out["degraded"] is False
    assert out["brief"]["summary"].startswith("Hot work")
    assert out["brief"]["hypotheses"]
    assert "response was not valid JSON" not in out["brief"]["openQuestions"]
