"""Model registry API — MLOps lifecycle view (spec §14 Phase 4).

Read-only view of the model registry: what is in production, what is in shadow/
canary, and each model's metrics. Promotion is an operator/CLI action, not a
web mutation, so this surface is GET-only.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from verge_mlops import ModelRouter

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models(request: Request, stage: str | None = None) -> dict:
    registry = request.app.state.model_registry
    cards = registry.list(stage=stage)
    return {
        "summary": registry.summary(),
        "models": [c.to_dict() for c in cards],
    }


@router.get("/models/route")
def route_model(request: Request, name: str, zone: str | None = None) -> dict:
    """Which model version serves a scoring request (production, or canary-by-zone)."""
    state = request.app.state
    router_ = ModelRouter(state.model_registry, getattr(state, "canary_zones", None))
    return router_.route(name, zone=zone).to_dict()
