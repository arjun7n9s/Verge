"""Alert fatigue metrics API (spec §4.6)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..fatigue_metrics import compute_fatigue_metrics

router = APIRouter(tags=["fatigue"])


@router.get("/fatigue/metrics")
def fatigue_metrics(request: Request) -> dict:
    """Measured S/N trend, FPR, and per-zone alert volume from live feedback."""
    return compute_fatigue_metrics(request.app.state.store)
