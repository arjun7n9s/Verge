"""Eval report API tests."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_eval_report_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("verge_api.routes.eval_report._EVAL_OUT", tmp_path)
    r = client.get("/api/eval/report")
    assert r.status_code == 404


def test_eval_report_returns_json_when_present(tmp_path, monkeypatch):
    sample = [{"incident": "vizag-2025-01", "verge": {"leadMin": 12.0, "band": "NEAR"}}]
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.json").write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setattr("verge_api.routes.eval_report._EVAL_OUT", out)
    r = client.get("/api/eval/report")
    assert r.status_code == 200
    assert r.json()[0]["incident"] == "vizag-2025-01"


def test_eval_aggregate_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("verge_api.routes.eval_report._EVAL_OUT", tmp_path)
    r = client.get("/api/eval/aggregate")
    assert r.status_code == 404


def test_eval_aggregate_returns_json_when_present(tmp_path, monkeypatch):
    sample = {"verge": {"misses": 0, "total": 4, "fnr": 0.0}}
    out = tmp_path / "out"
    out.mkdir()
    (out / "aggregate.json").write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setattr("verge_api.routes.eval_report._EVAL_OUT", out)
    r = client.get("/api/eval/aggregate")
    assert r.status_code == 200
    assert r.json()["verge"]["fnr"] == 0.0
