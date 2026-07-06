"""Plant layout routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from verge_twin.export import demo_geojson

router = APIRouter(tags=["plant"])


@router.get("/plant/geojson")
def plant_geojson() -> dict:
    """Zone polygons + sensor pins for the demo plant (console map)."""
    try:
        return demo_geojson()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
