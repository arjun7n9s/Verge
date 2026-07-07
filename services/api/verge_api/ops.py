"""Day-2 operability surface for plant IT (spec §14.6).

This is **not** the safety console. It is the surface the plant's IT team owns:
ingest health, sensor-health rollup, audit-chain integrity, model/build version,
last backup, and signed-bundle age. IT never logs into the operator console;
they have this plus a Prometheus scrape.

Everything here is honest: a fact we cannot measure (last backup time on a box
that has never backed up, signed-bundle age with no bundle metadata) is reported
as ``null`` with the reason implicit — never a fabricated timestamp. Backup and
bundle metadata come from the environment the deploy sets (``VERGE_LAST_BACKUP_TS``,
``VERGE_BUNDLE_BUILT_TS``); absence is a real, reportable state.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from verge_schema.enums import DataQuality

from .timescale_writer import timescale_status

_REPLAY_REPORT = Path(__file__).resolve().parents[3] / "eval/out/report.json"


def _age_seconds(ts_iso: str | None, now: datetime) -> float | None:
    if not ts_iso:
        return None
    try:
        ts = datetime.fromisoformat(ts_iso)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return round((now - ts).total_seconds(), 1)


def _last_replay_run(now: datetime) -> dict:
    if not _REPLAY_REPORT.exists():
        return {"ts": None, "ageSeconds": None}
    ts = datetime.fromtimestamp(_REPLAY_REPORT.stat().st_mtime, tz=UTC)
    return {"ts": ts.isoformat(), "ageSeconds": round((now - ts).total_seconds(), 1)}


def _model_registry(env: Mapping[str, str]) -> dict:
    """Registry summary: production model versions + stage rollup (§14 Phase 4)."""
    from verge_mlops import DEMO_REGISTRY, ModelRegistry

    path = env.get("VERGE_MODEL_REGISTRY") or str(DEMO_REGISTRY)
    if not Path(path).exists():
        return {"version": env.get("VERGE_MODEL_REGISTRY_VERSION") or None, "production": {}}
    summary = ModelRegistry.read_only(path).summary()
    return {"version": env.get("VERGE_MODEL_REGISTRY_VERSION") or None, **summary}


def _vision_health(vision) -> dict:
    """Probe the vision plane without letting it take down the health surface.

    A model-backed backend can raise on a probe (e.g. GPU/driver fault); the ops
    surface must report that as degraded, not crash (its whole job is to stay up
    when components don't)."""
    backend = getattr(vision, "backend", "stub")
    try:
        return {"backend": backend, "degraded": vision.detect("_ops_probe_").degraded}
    except Exception as exc:  # noqa: BLE001 - a probe failure is itself degradation
        return {"backend": backend, "degraded": True, "reason": f"probe failed: {exc}"}


def ops_snapshot(
    *,
    store,
    readings,
    llm,
    vision,
    version: str,
    started_at: datetime,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict:
    """Assemble the plant-IT operability snapshot."""
    env = env if env is not None else os.environ
    now = now or datetime.now(UTC)

    health = store.get_sensor_health()
    health_counts = {q.value: int(n) for q, n in health.items()}

    backup_ts = env.get("VERGE_LAST_BACKUP_TS") or None
    bundle_ts = env.get("VERGE_BUNDLE_BUILT_TS") or None

    return {
        "version": version,
        "uptimeSeconds": round((now - started_at).total_seconds(), 1),
        "audit": {
            "entries": store.audit_len(),
            "head": store.audit_head(),
            "verified": bool(store.audit_verify()),
        },
        "findings": {"total": len(store.list_findings(shadow=None))},
        "sensorHealth": {
            "counts": health_counts,
            "total": sum(health_counts.values()),
            # Guard on the SUM, not dict-nonempty: a dict of all-zero counts is
            # truthy but sums to 0 -> ZeroDivisionError would crash the surface.
            "livePct": (
                round(100 * health_counts.get(DataQuality.LIVE.value, 0) / _health_total)
                if (_health_total := sum(health_counts.values())) else None
            ),
        },
        "ingest": {
            "sensors": readings.sensor_count(),
            "readings": readings.reading_count(),
            "lastReadingTs": readings.latest_ts(),
        },
        "llm": {"provider": llm.name, "degraded": not llm.healthy()},
        "vision": _vision_health(vision),
        "modelRegistry": _model_registry(env),
        "backup": {"lastTs": backup_ts, "ageSeconds": _age_seconds(backup_ts, now)},
        "signedBundle": {"builtTs": bundle_ts, "ageSeconds": _age_seconds(bundle_ts, now)},
        "lastReplayRun": _last_replay_run(now),
        "timescale": timescale_status(env=env),
    }


def _metric(lines: list[str], name: str, value, help_: str, type_: str = "gauge") -> None:
    """Emit one Prometheus metric family (skips unmeasured/None values)."""
    if value is None:
        return
    lines.append(f"# HELP {name} {help_}")
    lines.append(f"# TYPE {name} {type_}")
    lines.append(f"{name} {value}")


def render_prometheus(snap: dict) -> str:
    """Render the snapshot as Prometheus text exposition format (v0.0.4).

    Dependency-free by design — the format is stable text, so plant IT scrapes it
    with no extra library on an air-gapped box (P2).
    """
    lines: list[str] = []
    version = snap["version"]
    lines.append("# HELP verge_build_info Build/version info")
    lines.append("# TYPE verge_build_info gauge")
    lines.append(f'verge_build_info{{version="{version}"}} 1')

    _metric(lines, "verge_uptime_seconds", snap["uptimeSeconds"], "Process uptime")
    _metric(lines, "verge_audit_entries", snap["audit"]["entries"], "Audit chain entries")
    _metric(lines, "verge_audit_verified", int(snap["audit"]["verified"]),
            "Audit chain integrity (1 ok, 0 broken)")
    _metric(lines, "verge_findings_total", snap["findings"]["total"], "Findings on record")
    _metric(lines, "verge_ingest_sensors", snap["ingest"]["sensors"], "Distinct sensors seen")
    _metric(lines, "verge_ingest_readings", snap["ingest"]["readings"], "Buffered reading points")
    _metric(lines, "verge_llm_degraded", int(snap["llm"]["degraded"]),
            "LLM narrative layer degraded (1 yes, 0 no)")
    _metric(lines, "verge_vision_degraded", int(snap["vision"]["degraded"]),
            "Vision plane degraded (1 yes, 0 no)")
    _metric(lines, "verge_models_total", snap["modelRegistry"].get("total"),
            "Models in the registry")
    _metric(lines, "verge_backup_age_seconds", snap["backup"]["ageSeconds"],
            "Age of the last audit/backup snapshot")
    _metric(lines, "verge_signed_bundle_age_seconds", snap["signedBundle"]["ageSeconds"],
            "Age of the installed signed bundle")

    # Sensor-health rollup as a labelled family.
    counts = snap["sensorHealth"]["counts"]
    if counts:
        lines.append("# HELP verge_sensor_health Sensors by data-quality state")
        lines.append("# TYPE verge_sensor_health gauge")
        for quality, n in sorted(counts.items()):
            lines.append(f'verge_sensor_health{{quality="{quality}"}} {n}')

    return "\n".join(lines) + "\n"
