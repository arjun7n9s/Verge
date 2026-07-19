"""Data-contract validation of canonical events (spec §14 Phase 4)."""

from __future__ import annotations

from verge_contracts import ContractRegistry, validate_stream

REG = ContractRegistry()

GOOD_READING = {
    "type": "reading", "ts": "2025-01-14T06:00:00+00:00", "sensorId": "LEL-04",
    "kind": "gas-lel", "unit": "%LEL", "zoneId": "B-04", "value": 71.0,
}
GOOD_PERMIT = {
    "type": "permit", "ts": "2025-01-14T05:30:00+00:00", "permitId": "PTW-1",
    "kind": "hot-work", "zoneId": "B-04",
}
GOOD_SHIFT = {
    "type": "shift", "ts": "2025-01-14T06:00:00+00:00", "zoneId": "B-04",
    "event": "changeover-start",
}


def test_valid_events_pass():
    for e in (GOOD_READING, GOOD_PERMIT, GOOD_SHIFT):
        assert REG.validate_event(e).valid, e


def test_reading_reports_versioned_contract():
    r = REG.validate_event(GOOD_READING)
    assert r.event_type == "reading" and r.contract_version == "1.0.0"


def test_missing_required_field_fails():
    bad = {k: v for k, v in GOOD_READING.items() if k != "value"}
    r = REG.validate_event(bad)
    assert not r.valid
    assert any("value" in e for e in r.errors)


def test_wrong_type_fails():
    bad = {**GOOD_READING, "value": "not-a-number"}
    r = REG.validate_event(bad)
    assert not r.valid
    assert any("value" in e and "number" in e for e in r.errors)


def test_bool_is_not_a_number():
    bad = {**GOOD_READING, "value": True}
    assert not REG.validate_event(bad).valid


def test_bad_timestamp_fails():
    bad = {**GOOD_READING, "ts": "14 January"}
    assert not REG.validate_event(bad).valid


def test_shift_event_choices_enforced():
    bad = {**GOOD_SHIFT, "event": "lunch-break"}
    r = REG.validate_event(bad)
    assert not r.valid
    assert any("one of" in e for e in r.errors)


def test_optional_permit_fields_are_optional():
    assert REG.validate_event(GOOD_PERMIT).valid  # no validFrom/validTo/equipmentId


def test_unknown_event_type_has_no_contract():
    r = REG.validate_event({"type": "telemetry", "ts": "2025-01-14T06:00:00"})
    assert not r.valid and "no contract" in r.errors[0]


def test_validate_stream_counts():
    report = validate_stream([GOOD_READING, {**GOOD_READING, "value": "x"}, GOOD_PERMIT])
    assert report["total"] == 3
    assert report["valid"] == 2
    assert report["invalid"] == 1
    assert report["violations"]


def test_registry_summary_lists_versions():
    summary = REG.summary()
    assert "reading" in summary["eventTypes"]
    assert summary["contracts"]["reading"] == ["1.0.0"]
    assert "voice-event" in summary["eventTypes"]
    assert "vision-detection" in summary["eventTypes"]
    assert "maintenance" in summary["eventTypes"]


def test_voice_and_vision_contracts_pass():
    voice = {
        "type": "voice-event",
        "ts": "2025-01-13T06:44:00+00:00",
        "transcript": "gas smell B-04",
        "zoneId": "B-04",
        "hazards": ["gas"],
    }
    vision = {
        "type": "vision-detection",
        "ts": "2025-01-13T06:44:00+00:00",
        "zoneId": "B-04",
        "cameraId": "CAM-1",
        "label": "ppe-missing",
        "confidence": 0.8,
    }
    assert REG.validate_event(voice).valid
    assert REG.validate_event(vision).valid


def test_nan_and_inf_readings_are_rejected():
    # Poison data: NaN/inf silently defeat threshold rules on a safety product.
    for bad in (float("nan"), float("inf"), float("-inf")):
        assert not REG.validate_event({**GOOD_READING, "value": bad}).valid


def test_latest_uses_semver_not_lexical_order():
    from verge_contracts import ContractRegistry, EventContract, FieldSpec

    v1 = EventContract("reading", "1.9.0", (FieldSpec("value", "number"),))
    v2 = EventContract("reading", "1.10.0", (FieldSpec("value", "number"),))
    reg = ContractRegistry([v1, v2])
    assert reg.latest("reading").version == "1.10.0"  # not "1.9.0"


def test_validate_stream_flags_truncation():
    events = [{**GOOD_READING, "value": "x"}] * 60  # 60 invalid, cap is 50
    report = validate_stream(events)
    assert report["invalid"] == 60
    assert report["violationsShown"] == 50
    assert report["violationsTruncated"] is True
