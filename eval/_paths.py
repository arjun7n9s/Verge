"""Dev-time path bootstrap so the harness runs from a checkout without install.

In production these are installed wheels (uv workspace); for the hackathon and
CI we just point sys.path at the in-repo packages.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for rel in ("packages/schema", "services/forecaster", "services/risk-engine"):
    p = str(_ROOT / rel)
    if p not in sys.path:
        sys.path.insert(0, p)

REPO_ROOT = _ROOT
