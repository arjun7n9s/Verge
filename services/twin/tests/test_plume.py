"""Gaussian plume exclusion zone tests."""

from verge_twin.plume import PlumeInput, exclusion_polygon


def test_exclusion_polygon_geojson():
    feature = exclusion_polygon(PlumeInput(source_x=10.0, source_y=20.0))
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert len(feature["geometry"]["coordinates"][0]) >= 4
