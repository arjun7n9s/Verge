"""Dev-time path bootstrap (mirrors eval/_paths). No-op once installed as wheels."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for rel in ("packages/schema", "services/forecaster", "services/risk-engine", "sims", "."):
    p = str(ROOT / rel)
    if p not in sys.path:
        sys.path.insert(0, p)
