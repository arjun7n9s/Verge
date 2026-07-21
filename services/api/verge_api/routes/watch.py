"""Continuous WatchLoop control — start / stop / status (product heartbeat)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..watch_loop import controller

router = APIRouter(tags=["watch"])


class WatchStartBody(BaseModel):
    intervalS: float | None = Field(default=None, ge=1.0, le=60.0)
    vision: bool | None = None
    voice: bool | None = None
    sensors: bool | None = None
    fuse: bool | None = None
    cognee: bool | None = None


def _legs_from_body(body: WatchStartBody) -> dict[str, bool] | None:
    legs: dict[str, bool] = {}
    for key in ("vision", "voice", "sensors", "fuse", "cognee"):
        val = getattr(body, key)
        if val is not None:
            legs[key] = val
    return legs or None


@router.get("/watch/status")
def watch_status() -> dict:
    return controller.public_status()


@router.post("/watch/start")
def watch_start(body: WatchStartBody, request: Request) -> dict:
    controller.bind_app(request.app)
    status = controller.start(interval_s=body.intervalS, legs=_legs_from_body(body))
    return {"ok": True, "watch": status}


@router.post("/watch/stop")
def watch_stop(request: Request) -> dict:
    controller.bind_app(request.app)
    status = controller.stop()
    return {"ok": True, "watch": status}
