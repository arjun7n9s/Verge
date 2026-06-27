"""Dev-time path wiring so `pytest` resolves the in-repo packages without install.

Production uses installed wheels (uv workspace); this keeps CI and a fresh
checkout green with a bare `pytest`.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
for rel in (
    "packages/schema",
    "packages/audit",
    "packages/llm",
    "services/forecaster",
    "services/risk-engine",
    "services/api",
    "services/edge-gateway",
    "sims",
    ".",  # eval is imported as a package from repo root
):
    p = str((ROOT / rel).resolve())
    if p not in sys.path:
        sys.path.insert(0, p)
