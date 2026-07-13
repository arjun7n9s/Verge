"""The deterministic tool loop.

model → (tool calls → execute → feed results back)* → final answer.

Hard bounds everywhere: max_steps caps the loop, every tool error is fed back
as data, and a degraded provider degrades the *agent* — one code path, checked
first, so the caller always gets an AgentResult and never an exception (P4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from verge_llm import LLMProvider, Message

from .tools import ToolRegistry


@dataclass
class AgentStep:
    tool: str
    arguments: dict
    result: str

    def to_wire(self) -> dict:
        return {"tool": self.tool, "arguments": self.arguments, "result": self.result}


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    degraded: bool = False
    reason: str | None = None
    model: str = ""

    def to_wire(self) -> dict:
        return {
            "answer": self.answer,
            "steps": [s.to_wire() for s in self.steps],
            "degraded": self.degraded,
            "reason": self.reason,
            "model": self.model,
        }


def run_tool_loop(
    provider: LLMProvider,
    *,
    system: str,
    user: str,
    tools: ToolRegistry,
    model: str | None = None,
    max_steps: int = 6,
    max_tokens: int = 1400,
) -> AgentResult:
    messages: list[Message] = [Message("system", system), Message("user", user)]
    steps: list[AgentStep] = []

    for _ in range(max_steps):
        completion = provider.chat(
            messages, tools=tools.to_openai(), model=model, max_tokens=max_tokens
        )
        if completion.degraded:
            return AgentResult(
                answer="", steps=steps, degraded=True,
                reason=completion.reason, model=completion.model,
            )
        if not completion.tool_calls:
            return AgentResult(answer=completion.text, steps=steps, model=completion.model)

        # Echo the assistant tool-call turn, then answer every call.
        messages.append(
            Message(
                "assistant",
                completion.text or "",
                tool_calls=tuple(tc.raw for tc in completion.tool_calls),
            )
        )
        for tc in completion.tool_calls:
            result = tools.execute(tc.name, tc.arguments)
            steps.append(AgentStep(tc.name, tc.arguments, result))
            messages.append(Message("tool", result, tool_call_id=tc.id))

    # Step budget exhausted: one final forced answer, no tools offered.
    final = provider.chat(messages, tools=None, model=model, max_tokens=max_tokens)
    return AgentResult(
        answer=final.text,
        steps=steps,
        degraded=final.degraded,
        reason=final.reason or ("step budget exhausted" if not final.degraded else final.reason),
        model=final.model,
    )
