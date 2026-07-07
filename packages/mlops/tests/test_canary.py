"""Canary zone parsing tests."""

from verge_mlops.canary import parse_canary_zones


def test_parse_canary_zones() -> None:
    zones = parse_canary_zones("compound-risk:B-04,B-05;other:Z-01")
    assert zones["compound-risk"] == {"B-04", "B-05"}
    assert zones["other"] == {"Z-01"}
