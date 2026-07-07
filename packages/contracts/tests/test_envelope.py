"""Event envelope and boundary validation tests."""

from __future__ import annotations

import pytest
from verge_contracts.envelope import ContractViolation, enrich_event, validate_and_enrich


def test_enrich_adds_event_id_and_site() -> None:
    event = enrich_event({
        "type": "reading",
        "ts": "2025-01-13T06:30:00+00:00",
        "sensorId": "LEL-04",
        "kind": "gas-lel",
        "unit": "%LEL",
        "zoneId": "B-04",
        "value": 12.0,
    }, site_id="plant-01")
    assert event["siteId"] == "plant-01"
    assert event["eventId"]
    assert event["schemaVersion"]
    assert event["ingestedAt"]


def test_validate_and_enrich_rejects_bad_reading() -> None:
    with pytest.raises(ContractViolation):
        validate_and_enrich({"type": "reading", "sensorId": "X", "value": "bad"})


def test_validate_and_enrich_accepts_finite_values() -> None:
    event = validate_and_enrich({
        "type": "reading",
        "ts": "2025-01-13T06:30:00+00:00",
        "sensorId": "LEL-04",
        "kind": "gas-lel",
        "unit": "%LEL",
        "zoneId": "B-04",
        "value": 12.0,
    })
    assert event["schemaVersion"] == "1.0.0"
