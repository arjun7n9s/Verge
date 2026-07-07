"""Commissioning summary for the operator console (spec §14.5)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["commission"])


@router.get("/commission/summary")
def commission_summary(request: Request) -> dict:
    """Six-step readiness report for the demo plant (cached after first run)."""
    cached = getattr(request.app.state, "commission_summary", None)
    if cached is None:
        from eval.commissioning import DEMO_LAYOUT, DEMO_SENSORS, run_commission

        report = run_commission("vizag-coke-oven", DEMO_LAYOUT, DEMO_SENSORS)
        cached = report.to_dict()
        request.app.state.commission_summary = cached
    return cached
