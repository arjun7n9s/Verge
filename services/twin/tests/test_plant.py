"""The plant model loads, exposes symmetric adjacency, and resolves thresholds."""

from verge_twin import load_plant


def test_demo_plant_loads() -> None:
    p = load_plant()
    assert p.name == "vizag-coke-oven"
    assert "B-04" in p.zones
    assert {"LEL-04", "CO-04", "LEL-05"} <= set(p.sensors)


def test_adjacency_is_symmetric() -> None:
    adj = load_plant().adjacency()
    assert "B-05" in adj["B-04"]
    assert "B-04" in adj["B-05"]  # symmetry filled even if only declared one way
    assert "B-03" in adj["B-04"]


def test_thresholds_by_kind_and_by_sensor() -> None:
    p = load_plant()
    assert p.thresholds_by_kind() == {"gas-lel": 100.0, "gas-co": 50.0}
    by_sensor = p.thresholds_by_sensor()
    assert by_sensor["LEL-04"] == 100.0 and by_sensor["CO-04"] == 50.0


def test_sensors_in_zone() -> None:
    p = load_plant()
    assert {s.sensor_id for s in p.sensors_in_zone("B-04")} == {"LEL-04", "CO-04"}


def test_demo_geojson_merges_zones_and_sensors() -> None:
    from verge_twin.export import demo_geojson

    doc = demo_geojson()
    assert doc["properties"]["plant"] == "vizag-coke-oven"
    assert len(doc["features"]) == 5
    b04 = next(f for f in doc["features"] if f["properties"]["zoneId"] == "B-04")
    assert "B-05" in b04["properties"]["adjacent"]
    assert any(s["sensorId"] == "LEL-04" for s in doc["sensors"])
