"""Post-transition hooks (memory ingest, etc.)."""

from __future__ import annotations

import os

from verge_memory import ingest_closed_finding
from verge_memory.client import CogneeClient
from verge_memory.datasets import dataset_name
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding

_CLOSED = {S.RESOLVED, S.CLOSED, S.SUPPRESSED_AS_DUPLICATE}


def maybe_ingest_closed_finding(finding: RiskFinding, *, to: S) -> None:
    """Best-effort Cognee ingest when a finding closes; never raises."""
    if to not in _CLOSED:
        return
    if os.environ.get("VERGE_COGNEE_ENABLED", "").lower() not in {"1", "true", "yes", "on"}:
        return
    try:
        client = CogneeClient.from_env(dict(os.environ))
        ingest_closed_finding(client, dataset_name(dict(os.environ)), finding)
    except Exception:
        return
