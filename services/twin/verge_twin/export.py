"""GeoJSON export for plant zone layouts (console map consumption)."""

from __future__ import annotations

import json
from pathlib import Path

from .plant import DEMO_PLANT, PLANTS_DIR, PlantModel, load_plant

DEFAULT_GEOJSON = PLANTS_DIR / "vizag-zones.geojson"


def geojson_for_plant(plant: PlantModel, geo_path: Path | None = None) -> dict:
    """Merge plant zone metadata with polygon features from a sidecar GeoJSON file."""
    geo_path = geo_path or DEFAULT_GEOJSON
    if not geo_path.exists():
        msg = f"zone geometry not found: {geo_path}"
        raise FileNotFoundError(msg)

    doc = json.loads(geo_path.read_text(encoding="utf-8"))
    features = doc.get("features", [])
    out_features = []
    for feat in features:
        props = dict(feat.get("properties") or {})
        zone_id = props.get("zoneId")
        if zone_id and zone_id in plant.zones:
            node = plant.zones[zone_id]
            props["name"] = node.name
            props["adjacent"] = sorted(node.adjacent)
        out_features.append({**feat, "properties": props})

    sensors = [
        {
            "sensorId": s.sensor_id,
            "kind": s.kind,
            "zoneId": s.zone_id,
            "threshold": s.threshold,
        }
        for s in plant.sensors.values()
    ]

    return {
        "type": "FeatureCollection",
        "properties": {"plant": plant.name},
        "features": out_features,
        "sensors": sensors,
    }


def demo_geojson() -> dict:
    return geojson_for_plant(load_plant(DEMO_PLANT))
