"""Graceful degradation matrix (spec §10.6) — operator-visible banners."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from verge_api.degradation import operator_banners
from verge_api.main import app

client = TestClient(app)


def test_llm_degraded_banner_when_provider_unhealthy() -> None:
    store = MagicMock()
    store.audit_verify.return_value = True
    store.get_sensor_health.return_value = {}
    llm = MagicMock()
    llm.healthy.return_value = False
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=False, reason="")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    banners = operator_banners(store=store, llm=llm, vision=vision, readings=readings)
    assert "llm-degraded" in {b["code"] for b in banners}


def test_audit_integrity_banner_when_chain_breaks() -> None:
    store = MagicMock()
    store.audit_verify.return_value = False
    store.get_sensor_health.return_value = {}
    llm = MagicMock()
    llm.healthy.return_value = True
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=False, reason="")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    banners = operator_banners(store=store, llm=llm, vision=vision, readings=readings)
    assert any(b["code"] == "audit-integrity-failed" for b in banners)


def test_ingest_lag_banner_from_env() -> None:
    store = MagicMock()
    store.audit_verify.return_value = True
    store.get_sensor_health.return_value = {}
    llm = MagicMock()
    llm.healthy.return_value = True
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=False, reason="")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    env = {"VERGE_INGEST_LAG_SECONDS": "47", "VERGE_INGEST_BUFFERED": "312"}
    banners = operator_banners(
        store=store, llm=llm, vision=vision, readings=readings, env=env,
    )
    lag = next(b for b in banners if b["code"] == "ingest-lag")
    assert "47s" in lag["message"]
    assert "312" in lag["message"]


def test_edge_autonomous_banner() -> None:
    store = MagicMock()
    store.audit_verify.return_value = True
    store.get_sensor_health.return_value = {}
    llm = MagicMock()
    llm.healthy.return_value = True
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=False, reason="")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    env = {
        "VERGE_EDGE_AUTONOMOUS": "true",
        "VERGE_EDGE_LAST_CENTRAL_SYNC": "2026-01-01T00:00:00+00:00",
    }
    banners = operator_banners(
        store=store, llm=llm, vision=vision, readings=readings, env=env,
    )
    assert any(b["code"] == "edge-autonomous" for b in banners)


def test_degradation_api_route() -> None:
    r = client.get("/api/degradation")
    assert r.status_code == 200
    body = r.json()
    assert "banners" in body
    assert isinstance(body["banners"], list)


def test_vision_degraded_banner() -> None:
    store = MagicMock()
    store.audit_verify.return_value = True
    store.get_sensor_health.return_value = {}
    llm = MagicMock()
    llm.healthy.return_value = True
    vision = MagicMock()
    vision.detect.return_value = MagicMock(degraded=True, reason="stub backend")
    readings = MagicMock()
    readings.latest_ts.return_value = None
    banners = operator_banners(store=store, llm=llm, vision=vision, readings=readings)
    assert any(b["code"] == "vision-degraded" for b in banners)
