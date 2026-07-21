"""One-click compound demo drill — wraps WatchLoop with a named scenario pack."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..demo_scenario import load_scenario
from ..watch_loop import controller

router = APIRouter(tags=["demo"])


class DemoStartBody(BaseModel):
    scenarioId: str = "compound-drill"
    intervalS: float | None = Field(default=None, ge=1.0, le=60.0)
    vision: bool | None = None
    voice: bool | None = None
    sensors: bool | None = None
    fuse: bool | None = None
    cognee: bool | None = None
    workers: bool | None = None


def _legs_from_body(body: DemoStartBody) -> dict[str, bool] | None:
    legs: dict[str, bool] = {}
    for key in ("vision", "voice", "sensors", "fuse", "cognee", "workers"):
        val = getattr(body, key)
        if val is not None:
            legs[key] = val
    return legs or None


@router.get("/demo/status")
def demo_status() -> dict:
    st = controller.public_status()
    return {
        "ok": True,
        "demo": st.get("mode") == "demo" and st.get("running"),
        "watch": st,
    }


@router.get("/demo/scenarios/{scenario_id}")
def demo_scenario_meta(scenario_id: str) -> dict:
    try:
        pack = load_scenario(scenario_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "id": pack.id,
        "name": pack.name,
        "label": pack.label,
        "coach": pack.coach,
        "durationS": pack.duration_s,
        "intervalS": pack.interval_s,
        "zonePrimary": pack.zone_primary,
        "radioCues": len(pack.radio),
        "wavPresent": sum(1 for c in pack.radio if c.path is not None),
        "workerCues": len(pack.workers),
    }


@router.post("/demo/start")
def demo_start(body: DemoStartBody, request: Request) -> dict:
    try:
        load_scenario(body.scenarioId)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    controller.bind_app(request.app)
    if controller.status.running:
        controller.stop()
    status = controller.start_demo(
        scenario_id=body.scenarioId,
        interval_s=body.intervalS,
        legs=_legs_from_body(body),
    )
    return {"ok": True, "demo": True, "watch": status}


@router.post("/demo/stop")
def demo_stop(request: Request) -> dict:
    controller.bind_app(request.app)
    status = controller.stop()
    return {"ok": True, "demo": False, "watch": status}
