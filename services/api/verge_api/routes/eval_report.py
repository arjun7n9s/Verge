"""Eval harness report surface for operators and auditors (spec §10)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["eval"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_EVAL_OUT = _REPO_ROOT / "eval" / "out"


@router.get("/eval/report")
def eval_report() -> list:
    """Latest replay harness output (``eval/out/report.json``)."""
    path = _EVAL_OUT / "report.json"
    if not path.is_file():
        raise HTTPException(
            404,
            "eval report not found — run `make eval` or `uv run verge replay --all`",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise HTTPException(500, "eval report.json must be a JSON array")
    return data


@router.get("/eval/aggregate")
def eval_aggregate() -> dict:
    """False-negative-rate rollup across every replayed incident (``eval/out/aggregate.json``).

    Misses/total/FNR per method (verge vs. b0/b1/b2) — the brief's own framing:
    "the metric that actually saves lives."
    """
    path = _EVAL_OUT / "aggregate.json"
    if not path.is_file():
        raise HTTPException(
            404,
            "eval aggregate not found — run `make eval` or `uv run python -m eval.harness --all`",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HTTPException(500, "eval aggregate.json must be a JSON object")
    return data
