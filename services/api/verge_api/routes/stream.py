"""Live stream status for operators and plant IT."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..redpanda_fanout import fanout_enabled

router = APIRouter(tags=["stream"])


@router.get("/stream/status")
def stream_status(request: Request) -> dict:
    bus = getattr(request.app.state, "stream_bus", None)
    return {
        "subscribers": len(getattr(bus, "_queues", [])) if bus else 0,
        "redpandaFanout": getattr(request.app.state, "stream_fanout_active", False),
        "fanoutConfigured": fanout_enabled(),
    }
