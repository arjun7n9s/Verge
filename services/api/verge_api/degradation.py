"""Operator-visible degradation banners (spec §10.6).

Maps platform posture to the exact copy the console should show when a subsystem
is degraded. Never fabricates sync times or delivery status (P4).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime


def _age_minutes(ts_iso: str | None, now: datetime) -> int | None:
    if not ts_iso:
        return None
    try:
        ts = datetime.fromisoformat(ts_iso)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return max(0, int((now - ts).total_seconds() // 60))


def operator_banners(
    *,
    store,
    llm,
    vision,
    readings,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    stream_fanout_active: bool = False,
    stream_fanout_configured: bool = False,
    timescale: dict | None = None,
) -> list[dict]:
    """Return active operator banners for the console ribbon."""
    env = env if env is not None else os.environ
    now = now or datetime.now(UTC)
    banners: list[dict] = []

    if not llm.healthy():
        banners.append({
            "code": "llm-degraded",
            "severity": "warn",
            "message": (
                "AI narrative: degraded (provider unavailable). "
                "Safety alerts and rule engine remain current."
            ),
        })

    if not store.audit_verify():
        banners.append({
            "code": "audit-integrity-failed",
            "severity": "critical",
            "message": (
                "Audit integrity check failed — read-only mode recommended; "
                "ops notified."
            ),
        })

    try:
        v = vision.detect("_degradation_probe_")
        if v.degraded:
            banners.append({
                "code": "vision-degraded",
                "severity": "warn",
                "message": (
                    f"Vision plane: degraded ({v.reason or 'no GPU/model configured'}). "
                    "Compound findings may omit frame lineage."
                ),
            })
    except Exception as exc:  # noqa: BLE001
        banners.append({
            "code": "vision-degraded",
            "severity": "warn",
            "message": f"Vision plane: degraded (probe failed: {type(exc).__name__}).",
        })

    lag_s = env.get("VERGE_INGEST_LAG_SECONDS")
    if lag_s:
        try:
            lag = float(lag_s)
            if lag > 30:
                buffered = env.get("VERGE_INGEST_BUFFERED", "0")
                banners.append({
                    "code": "ingest-lag",
                    "severity": "warn",
                    "message": (
                        f"Ingest gap: {int(lag)}s · {buffered} events buffered."
                    ),
                })
        except ValueError:
            pass

    if env.get("VERGE_EDGE_AUTONOMOUS", "").lower() in {"1", "true", "yes"}:
        last_sync = env.get("VERGE_EDGE_LAST_CENTRAL_SYNC")
        age = _age_minutes(last_sync, now)
        sync_text = f"{age}m ago" if age is not None else "unknown"
        banners.append({
            "code": "edge-autonomous",
            "severity": "info",
            "message": f"Edge mode · autonomous · last central sync {sync_text}.",
        })

    drift_model = env.get("VERGE_DRIFT_MODEL")
    if drift_model:
        banners.append({
            "code": "model-drift",
            "severity": "warn",
            "message": (
                f"{drift_model}: rules-only · drift detected · retraining queued."
            ),
        })

    graph_pct = env.get("VERGE_GRAPH_COVERAGE_PCT")
    if graph_pct:
        try:
            pct = float(graph_pct)
            if pct < 100:
                zone = env.get("VERGE_GRAPH_COVERAGE_ZONE", "site")
                banners.append({
                    "code": "graph-incomplete",
                    "severity": "info",
                    "message": (
                        f"Graph coverage at {pct:.0f}% for zone {zone} — "
                        "some findings use sensor-only rules."
                    ),
                })
        except ValueError:
            pass

    last_reading = readings.latest_ts()
    stale_min = _age_minutes(last_reading, now) if last_reading else None
    if stale_min is not None and stale_min >= 12:
        banners.append({
            "code": "sensor-stale",
            "severity": "warn",
            "message": (
                f"Sensor ingest stale ({stale_min}m since last reading) — "
                "check edge gateway connectivity."
            ),
        })

    if stream_fanout_configured and not stream_fanout_active:
        banners.append({
            "code": "stream-fanout-degraded",
            "severity": "warn",
            "message": (
                "Live stream fan-out: Redpanda consumer unavailable — "
                "console updates on API ingest only."
            ),
        })

    if timescale is not None and timescale.get("configured") and timescale.get("degraded"):
        reason = timescale.get("reason", "connection failed")
        banners.append({
            "code": "timescale-degraded",
            "severity": "warn",
            "message": (
                f"Timescale telemetry: degraded ({reason}) — "
                "using in-memory ring buffer only."
            ),
        })

    try:
        from verge_voice import speechmatics_status

        stt = speechmatics_status(dict(env))
        if stt.get("degraded"):
            banners.append({
                "code": "speechmatics-degraded",
                "severity": "warn",
                "message": (
                    "Radio/voice STT: degraded ("
                    f"{stt.get('reason') or 'Speechmatics unavailable'}). "
                    "Text handover and rule engine remain available."
                ),
            })
    except Exception as exc:  # noqa: BLE001
        banners.append({
            "code": "speechmatics-degraded",
            "severity": "warn",
            "message": f"Radio/voice STT: degraded (probe failed: {type(exc).__name__}).",
        })

    try:
        from verge_memory.client import CogneeClient

        client = CogneeClient.from_env(dict(env))
        settings = client.settings
        # Config-only (no network). Live Cognee health lives on /api/memory/status.
        if settings.enabled and not settings.ready:
            banners.append({
                "code": "cognee-degraded",
                "severity": "warn",
                "message": (
                    "Plant memory (Cognee): degraded ("
                    f"{settings.missing_reason() or 'not ready'}). "
                    "DocIntel local corpus still answers when available."
                ),
            })
    except Exception as exc:  # noqa: BLE001
        banners.append({
            "code": "cognee-degraded",
            "severity": "warn",
            "message": f"Plant memory (Cognee): degraded (status failed: {type(exc).__name__}).",
        })

    return banners
