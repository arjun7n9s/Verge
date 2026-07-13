"""Tool loop mechanics with a scripted provider — no network, fully deterministic."""

from __future__ import annotations

import json

from verge_agents import Tool, ToolRegistry, investigate, run_tool_loop
from verge_llm import Completion, NullProvider, ToolCall


class ScriptedProvider:
    """Plays back a fixed sequence of completions; records what it was sent."""

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


def _registry() -> ToolRegistry:
    return ToolRegistry([
        Tool("lookup", "Look up a value.",
             lambda key="": {"key": key, "value": 42},
             {"type": "object", "properties": {"key": {"type": "string"}}}),
        Tool("explode", "Always fails.", lambda: 1 / 0),
    ])


def _call(name: str, args: dict, cid: str = "c1") -> ToolCall:
    raw = {"id": cid, "type": "function",
           "function": {"name": name, "arguments": json.dumps(args)}}
    return ToolCall(id=cid, name=name, arguments=args, raw=raw)


def test_loop_executes_tools_then_returns_answer():
    provider = ScriptedProvider([
        Completion("", "m", tool_calls=(_call("lookup", {"key": "lel"}),)),
        Completion("The LEL value is 42.", "m"),
    ])
    result = run_tool_loop(provider, system="s", user="u", tools=_registry())
    assert result.answer == "The LEL value is 42."
    assert [s.tool for s in result.steps] == ["lookup"]
    assert json.loads(result.steps[0].result)["value"] == 42
    # Second call must include the tool result transcript (role=tool message).
    roles = [m.role for m in provider.calls[1]["messages"]]
    assert "tool" in roles and "assistant" in roles


def test_tool_error_fed_back_not_raised():
    provider = ScriptedProvider([
        Completion("", "m", tool_calls=(_call("explode", {}),)),
        Completion("done", "m"),
    ])
    result = run_tool_loop(provider, system="s", user="u", tools=_registry())
    assert result.answer == "done"
    assert "failed" in json.loads(result.steps[0].result)["error"]


def test_unknown_tool_reported_to_model():
    provider = ScriptedProvider([
        Completion("", "m", tool_calls=(_call("nope", {}),)),
        Completion("ok", "m"),
    ])
    result = run_tool_loop(provider, system="s", user="u", tools=_registry())
    assert "unknown tool" in json.loads(result.steps[0].result)["error"]


def test_step_budget_forces_final_answer():
    calls = [Completion("", "m", tool_calls=(_call("lookup", {"key": "x"}, f"c{i}"),))
             for i in range(3)]
    provider = ScriptedProvider([*calls, Completion("forced wrap-up", "m")])
    result = run_tool_loop(provider, system="s", user="u", tools=_registry(), max_steps=3)
    assert result.answer == "forced wrap-up"
    assert len(result.steps) == 3
    # The forced final call must offer no tools.
    assert provider.calls[-1]["tools"] is None


def test_degraded_provider_degrades_agent():
    result = run_tool_loop(NullProvider(), system="s", user="u", tools=_registry())
    assert result.degraded is True
    assert result.answer == ""


def test_investigator_parses_brief_and_carries_evidence():
    brief = {"summary": "Hot work near rising LEL.",
             "hypotheses": [{"cause": "purge failure", "likelihood": "high",
                             "supportedBy": "get_recent_telemetry"}],
             "recommendedBarriers": [], "regulatoryRefs": [], "openQuestions": []}
    provider = ScriptedProvider([
        Completion("", "m", tool_calls=(_call("lookup", {"key": "t"}),)),
        Completion(json.dumps(brief), "m"),
    ])
    out = investigate(provider, finding_id="F-1", zone_id="B-04", title="t",
                      tools=_registry())
    assert out["degraded"] is False
    assert out["brief"]["summary"] == "Hot work near rising LEL."
    assert out["brief"]["hypotheses"][0]["likelihood"] == "high"
    assert [e["tool"] for e in out["evidence"]] == ["lookup"]


def test_investigator_degraded_path_is_fact_sheet():
    out = investigate(NullProvider(), finding_id="F-1", zone_id="B-04", title="t",
                      tools=_registry())
    assert out["degraded"] is True
    assert "no LLM" in out["brief"]["summary"]
    # No fabricated hypotheses in the deterministic path (P4).
    assert out["brief"]["hypotheses"] == []


def test_non_json_answer_flagged_not_faked():
    provider = ScriptedProvider([Completion("plain prose, no JSON", "m")])
    out = investigate(provider, finding_id="F-1", zone_id="B-04", title="t",
                      tools=_registry())
    assert out["brief"]["summary"].startswith("plain prose")
    assert "response was not valid JSON" in out["brief"]["openQuestions"]
