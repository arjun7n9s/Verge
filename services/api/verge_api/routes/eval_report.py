"""Eval harness report surface for operators and auditors (spec §10)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["eval"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_EVAL_OUT = _REPO_ROOT / "eval" / "out"


@router.get("/eval/report")
def eval_report() -> dict:
    """Latest replay harness output (``eval/out/report.json``)."""
    path = _EVAL_OUT / "report.json"
    if not path.is_file():
        raise HTTPException(
            404,
            "eval report not found — run `make eval` or `uv run verge replay --all`",
        )
    return json.loads(path.read_text(encoding="utf-8"))
