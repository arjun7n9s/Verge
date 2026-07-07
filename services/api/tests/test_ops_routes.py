"""Plant-IT operability surface: /api/ops/status + /metrics (spec §14.6)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_api.ops import ops_snapshot, render_prometheus

client = TestClient(app)


def test_ops_status_reports_audit_integrity_and_ingest():
    body = client.get("/api/ops/status").json()
    assert body["version"]
    assert body["audit"]["verified"] is True
    assert body["audit"]["entries"] >= 0
    # The demo seed hydrates the reading buffer from the Vizag replay.
    assert body["ingest"]["sensors"] > 0
    assert body["ingest"]["readings"] > 0
    assert "livePct" in body["sensorHealth"]


def test_ops_status_is_honest_about_unmeasured_facts():
    body = client.get("/api/ops/status").json()
    # No backup/bundle env set in the test host -> reported as null, not faked.
    assert body["backup"]["lastTs"] is None
    assert body["backup"]["ageSeconds"] is None
    assert body["signedBundle"]["builtTs"] is None


def test_metrics_prometheus_exposition_format():
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "verge_build_info" in text
    assert "verge_audit_verified 1" in text
    assert "# TYPE verge_audit_entries gauge" in text
    # Labelled family for sensor health.
    assert "verge_sensor_health{quality=" in text or "verge_findings_total" in text


def test_livepct_handles_all_zero_counts_without_crashing():
    from datetime import UTC, datetime

    from verge_schema.enums import DataQuality

    class _ZeroHealthStore:
        def get_sensor_health(self):
            return {DataQuality.STALE: 0}  # truthy dict, sums to 0

        def audit_len(self):
            return 0

        def audit_head(self):
            return "0" * 64

        def audit_verify(self):
            return True

        def list_findings(self, shadow=None):
            return []

    snap = ops_snapshot(
        store=_ZeroHealthStore(),
        readings=app.state.readings,
        llm=app.state.llm,
        vision=app.state.vision,
        version="9.9.9",
        started_at=datetime.now(UTC),
        env={},
    )
    assert snap["sensorHealth"]["livePct"] is None  # no crash, honest null


def test_vision_probe_failure_degrades_not_crashes():
    class _BoomVision:
        backend = "ultralytics"

        def detect(self, *a, **k):
            raise RuntimeError("GPU fault")

    from datetime import UTC, datetime

    snap = ops_snapshot(
        store=app.state.store, readings=app.state.readings, llm=app.state.llm,
        vision=_BoomVision(), version="9.9.9", started_at=datetime.now(UTC), env={},
    )
    assert snap["vision"]["degraded"] is True
    assert "probe failed" in snap["vision"]["reason"]


def test_render_skips_unmeasured_and_backup_age_absent():
    snap = ops_snapshot(
        store=app.state.store,
        readings=app.state.readings,
        llm=app.state.llm,
        vision=app.state.vision,
        version="9.9.9",
        started_at=datetime.now(UTC),
        env={},  # no backup/bundle metadata
    )
    text = render_prometheus(snap)
    assert 'verge_build_info{version="9.9.9"}' in text
    # An unmeasured metric (backup age) must be omitted entirely, not emitted null.
    assert "verge_backup_age_seconds" not in text
