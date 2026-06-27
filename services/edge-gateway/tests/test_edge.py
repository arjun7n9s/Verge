"""Normalization repairs/rejects dirty OT data; store-and-forward never drops
safety data on a blip (until bounded, and then it counts)."""

import pytest

from verge_edge import (
    NormalizationError,
    StoreAndForward,
    normalize_mqtt,
    normalize_opcua,
)


def test_normalize_mqtt_reading() -> None:
    e = normalize_mqtt(
        "verge/reading/B-04/LEL-04",
        b'{"sensorId":"LEL-04","kind":"gas-lel","unit":"%LEL","value":91.5,"ts":1736750640}',
    )
    assert e["type"] == "reading"
    assert e["sensorId"] == "LEL-04"
    assert e["value"] == 91.5
    assert e["zoneId"] == "B-04"
    assert e["ts"].endswith("+00:00")


def test_zone_backfilled_from_topic() -> None:
    e = normalize_mqtt("verge/reading/B-04/CO-04", b'{"sensorId":"CO-04","value":40}')
    assert e["zoneId"] == "B-04"


def test_bad_topic_and_missing_field_rejected() -> None:
    with pytest.raises(NormalizationError):
        normalize_mqtt("nope/reading/x", b"{}")
    with pytest.raises(NormalizationError):
        normalize_mqtt("verge/reading/B-04/X", b'{"value": 1}')  # no sensorId


def test_opcua_requires_mapping() -> None:
    mapping = {"ns=2;s=LEL04": {"sensorId": "LEL-04", "kind": "gas-lel", "unit": "%LEL",
                                "zoneId": "B-04"}}
    e = normalize_opcua("ns=2;s=LEL04", 91.5, mapping=mapping)
    assert e["sensorId"] == "LEL-04"
    with pytest.raises(NormalizationError):
        normalize_opcua("ns=2;s=UNKNOWN", 1.0, mapping=mapping)


def test_store_and_forward_buffers_then_flushes() -> None:
    sink_out: list[dict] = []
    saf = StoreAndForward()
    saf.submit({"n": 1}, sink_out.append)  # online -> straight through
    assert sink_out == [{"n": 1}]

    saf.go_offline()
    saf.submit({"n": 2}, sink_out.append)
    saf.submit({"n": 3}, sink_out.append)
    assert saf.buffered == 2 and sink_out == [{"n": 1}]  # nothing new went out

    forwarded = saf.reconnect(sink_out.append)
    assert forwarded == 2
    assert sink_out == [{"n": 1}, {"n": 2}, {"n": 3}]  # order preserved


def test_bounded_buffer_counts_drops() -> None:
    saf = StoreAndForward(maxlen=2)
    saf.go_offline()
    for i in range(5):
        saf.submit({"n": i}, lambda e: None)
    assert saf.buffered == 2
    assert saf.dropped == 3  # surfaced, never silent
