"""Gas dispersion exclusion zones (spec §5)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from verge_twin.export import geojson_for_plant
from verge_twin.plant import DEMO_PLANT, load_plant
from verge_twin.plume import PlumeInput, exclusion_polygon

router = APIRouter(tags=["plume"])


def _zone_centroid_geo(plant, zone_id: str) -> tuple[float, float]:
    if zone_id not in plant.zones:
        raise HTTPException(404, "zone not found")
    doc = geojson_for_plant(plant)
    for feat in doc.get("features", []):
        props = feat.get("properties") or {}
        if props.get("zoneId") != zone_id:
            continue
        ring = feat["geometry"]["coordinates"][0]
        pts = ring[:-1] or ring
        n = len(pts) or 1
        lng = sum(p[0] for p in pts) / n
        lat = sum(p[1] for p in pts) / n
        return lng, lat
    raise HTTPException(404, "zone geometry not found")


@router.get("/zones/{zone_id}/exclusion")
def zone_exclusion(
    zone_id: str,
    wind_speed: float = Query(3.0, alias="windSpeedMs"),
    wind_dir: float = Query(270.0, alias="windDirDeg"),
    release_rate: float = Query(0.5, alias="releaseRateKgS"),
) -> dict:
    """Gaussian plume GeoJSON for map overlay during a leak scenario."""
    plant = load_plant(DEMO_PLANT)
    lng, lat = _zone_centroid_geo(plant, zone_id)
    # Plume model uses local meters; ~1e-4 deg/m at this latitude.
    scale = 1 / 111_000
    feature = exclusion_polygon(PlumeInput(
        source_x=0.0,
        source_y=0.0,
        release_rate_kg_s=release_rate,
        wind_speed_m_s=wind_speed,
        wind_dir_deg=wind_dir,
    ))
    ring = feature["geometry"]["coordinates"][0]
    feature["geometry"]["coordinates"][0] = [
        [lng + x * scale, lat + y * scale] for x, y in ring
    ]
    feature["properties"]["zoneId"] = zone_id
    return {"zoneId": zone_id, "exclusion": feature}
