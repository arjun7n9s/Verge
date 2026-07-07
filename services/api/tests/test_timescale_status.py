"""Timescale status and degradation banner tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from verge_api.degradation import operator_banners
from verge_api.main import app
from verge_api.timescale_writer import query_sensor_series, timescale_status

client = TestClient(app)


def test_timescale_status_unconfigured():
    assert timescale_status(env={})["configured"] is False


def test_query_sensor_series_skips_without_dsn():
    assert query_sensor_series(["LEL-04"], env={}) == {}


def test_stream_fanout_degraded_banner():
    store = MagicMock()
    store.audit_verify.return_value = True
    llm = MagicMock()
    llm.healthy.return_value = True
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=False, reason="")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    banners = operator_banners(
        store=store,
        llm=llm,
        vision=vision,
        readings=readings,
        stream_fanout_configured=True,
        stream_fanout_active=False,
    )
    assert any(b["code"] == "stream-fanout-degraded" for b in banners)


def test_timescale_degraded_banner():
    store = MagicMock()
    store.audit_verify.return_value = True
    llm = MagicMock()
    llm.healthy.return_value = True
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=False, reason="")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    banners = operator_banners(
        store=store,
        llm=llm,
        vision=vision,
        readings=readings,
        timescale={"configured": True, "degraded": True, "reason": "OperationalError"},
    )
    assert any(b["code"] == "timescale-degraded" for b in banners)


def test_timescale_status_route():
    r = client.get("/api/timescale/status")
    assert r.status_code == 200
    body = r.json()
    assert "configured" in body
