"""Compound Risk Engine + sensor-health plane (spec §4.1, §4.7). LLM-independent."""

from pathlib import Path

from .context import RiskContext, ZoneView
from .engine import evaluate
from .health import classify, is_degraded, ribbon
from .rules import Rule, load_rules

STARTER_RULES = Path(__file__).parent / "rules"

__all__ = [
    "STARTER_RULES",
    "RiskContext",
    "Rule",
    "ZoneView",
    "classify",
    "evaluate",
    "is_degraded",
    "load_rules",
    "ribbon",
]
__version__ = "0.3.0"
