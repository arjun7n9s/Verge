"""Verge agents — deterministic tool-loop agents over platform data (advisory only)."""

from .investigator import investigate
from .loop import AgentResult, AgentStep, run_tool_loop
from .tools import Tool, ToolRegistry

__all__ = [
    "AgentResult",
    "AgentStep",
    "Tool",
    "ToolRegistry",
    "investigate",
    "run_tool_loop",
]
__version__ = "0.3.0"
