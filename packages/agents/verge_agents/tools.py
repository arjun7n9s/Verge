"""Tool registry for Verge agents.

A Tool is a named, described, JSON-schema'd python callable. Agents only ever
get **read-only** tools over platform data — an agent can investigate, it can
never actuate (P8: the operator is the only interlock). No framework: the
OpenAI function-calling wire shape is ~20 lines, and owning them keeps the
stack sovereign/air-gap portable (P2).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def to_openai(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools or []:
            self.register(t)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name {tool.name!r}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def to_openai(self) -> list[dict]:
        return [self._tools[n].to_openai() for n in self.names()]

    def execute(self, name: str, arguments: dict) -> str:
        """Run a tool; ALWAYS returns a string (JSON) — an exception becomes an
        error payload the model can read, never a crash of the loop."""
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"unknown tool {name!r}", "available": self.names()})
        try:
            result = tool.fn(**arguments)
        except TypeError as exc:  # bad/missing arguments from the model
            return json.dumps({"error": f"bad arguments for {name}: {exc}"})
        except Exception as exc:  # tool itself failed — report, don't raise
            return json.dumps({"error": f"{name} failed: {type(exc).__name__}: {exc}"})
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, default=str)
        except (TypeError, ValueError):
            return json.dumps({"result": str(result)})
