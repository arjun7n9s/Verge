"""Post-transition / voice hooks (memory ingest, etc.). Never raise to callers."""

from __future__ import annotations

import os

from verge_memory.client import CogneeClient, cognee_enabled_from_env
from verge_memory.datasets import dataset_name
from verge_memory.ingest import ingest_and_cognify, ingest_closed_finding, ingest_feedback
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding

_CLOSED = {S.RESOLVED, S.CLOSED, S.SUPPRESSED_AS_DUPLICATE}


def _memory_enabled(env: dict[str, str] | None = None) -> bool:
    """Same gate as doc cognify: auto-on when keys present; false forces off."""
    return cognee_enabled_from_env(env or dict(os.environ))


def maybe_ingest_closed_finding(finding: RiskFinding, *, to: S) -> None:
    """Best-effort Cognee ingest when a finding closes; never raises."""
    if to not in _CLOSED or not _memory_enabled():
        return
    try:
        env = dict(os.environ)
        client = CogneeClient.from_env(env)
        ingest_closed_finding(client, dataset_name(env), finding)
    except Exception:
        return


def maybe_ingest_feedback(
    finding: RiskFinding,
    *,
    verdict: str,
    reason_code: str | None,
    reason_text: str | None,
) -> None:
    """Best-effort Cognee ingest of operator feedback; never raises."""
    if not _memory_enabled():
        return
    try:
        env = dict(os.environ)
        client = CogneeClient.from_env(env)
        ingest_feedback(
            client,
            dataset_name(env),
            finding,
            verdict=verdict,
            reason_code=reason_code,
            reason_text=reason_text,
        )
    except Exception:
        return


def maybe_ingest_near_miss(
    transcript: str, *, structured: dict, finding_id: str | None = None
) -> dict:
    """Best-effort Cognee add+cognify of an operator-reported near-miss / radio.

    Returns a small status dict for route responses; never raises.
    """
    if not _memory_enabled() or not transcript.strip():
        return {"degraded": True, "reason": "cognee-disabled-or-empty"}
    try:
        env = dict(os.environ)
        client = CogneeClient.from_env(env)
        if not client.settings.ready:
            return {
                "degraded": True,
                "reason": client.settings.missing_reason() or "cognee-not-ready",
            }
        summary = structured.get("summary") or transcript[:240]
        title = f"Near-miss report{f' (linked to {finding_id})' if finding_id else ''}"
        hazards = ", ".join(structured.get("hazards", []) or []) or "none noted"
        zones = ", ".join(structured.get("zones", []) or []) or "none noted"
        actions = ", ".join(structured.get("actions", []) or []) or "none noted"
        body = (
            f"{summary}\n\n"
            f"Hazards: {hazards}\n"
            f"Zones: {zones}\n"
            f"Actions: {actions}\n\n"
            f"Full English ops transcript:\n{transcript}"
        )
        result = ingest_and_cognify(client, dataset_name(env), title, body)
        return {
            "degraded": bool(result.degraded),
            "reason": result.reason or "",
            "statusCode": result.status_code,
        }
    except Exception as exc:
        return {"degraded": True, "reason": f"cognee:{type(exc).__name__}"}


def maybe_ingest_voice_ops(
    transcript: str,
    *,
    structured: dict,
    source: str = "radio",
    finding_id: str | None = None,
) -> dict:
    """Alias for radio/handover English ops → searchable Cognee memory."""
    if not transcript.strip():
        return {"degraded": True, "reason": "empty-transcript"}
    # Reuse near-miss cognify path with a source-aware title prefix via finding_id/source.
    structured = dict(structured or {})
    if source and not structured.get("summary"):
        structured["summary"] = f"{source}: {transcript[:200]}"
    return maybe_ingest_near_miss(
        transcript, structured=structured, finding_id=finding_id
    )
