"""Compound hot-work finding: single legs insufficient; multi-source fires."""

from datetime import UTC, datetime, timedelta

from verge_risk import STARTER_RULES, evaluate, load_rules
from verge_risk.context import RiskContext
from verge_schema.core import Permit, Reading, Sensor
from verge_schema.events import VisionDetection, VoiceEvent

NOW = datetime(2025, 1, 13, 6, 44, tzinfo=UTC)
RULES = load_rules(STARTER_RULES)
COMPOUND = "compound hot-work gas risk"


def _permit() -> Permit:
    return Permit(
        permit_id="PW-0142",
        kind="hot-work",
        zone_id="B-04",
        valid_from=NOW - timedelta(hours=1),
        valid_to=NOW + timedelta(hours=1),
    )


def _lel_sensor() -> Sensor:
    return Sensor(
        sensor_id="LEL-04",
        kind="gas-lel",
        unit="%LEL",
        zone_id="B-04",
        expected_cadence_s=1.0,
        plausible_min=0.0,
        plausible_max=100.0,
    )


def _reads(values: list[float]) -> list[Reading]:
    return [
        Reading(
            sensor_id="LEL-04",
            ts=NOW - timedelta(seconds=(len(values) - 1 - i) * 30),
            value=float(v),
        )
        for i, v in enumerate(values)
    ]


def _voice() -> VoiceEvent:
    return VoiceEvent(
        event_id="VE-1",
        ts=NOW - timedelta(minutes=1),
        transcript="smell of gas near B-04, check LEL",
        zone_id="B-04",
        hazards=["gas", "smell", "lel"],
        source="radio",
    )


def _vision() -> VisionDetection:
    return VisionDetection(
        detection_id="VD-1",
        ts=NOW - timedelta(seconds=20),
        camera_id="CAM-B04",
        zone_id="B-04",
        label="person",
        confidence=0.81,
    )


def test_compound_requires_voice_lel_and_vision() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={"LEL-04": _lel_sensor()},
        readings={"LEL-04": _reads([40.0, 42.0, 45.0, 48.0])},
        permits=[_permit()],
        thresholds={"gas-lel": 100.0},
        voice_events=[_voice()],
        vision_detections=[_vision()],
    )
    findings = evaluate(ctx, RULES)
    hit = next(f for f in findings if COMPOUND in f.title.lower())
    kinds = {s.kind for s in hit.contributing_signals}
    assert {"voice", "reading", "vision", "permit"} <= kinds
    assert any(x.startswith("voice:") for x in hit.lineage)
    assert any(x.startswith("reading:") for x in hit.lineage)
    assert any(x.startswith("vision:") for x in hit.lineage)


def test_low_lel_alone_no_compound() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={"LEL-04": _lel_sensor()},
        readings={"LEL-04": _reads([4.0, 5.0, 6.0, 7.0])},
        permits=[_permit()],
        thresholds={"gas-lel": 100.0},
        voice_events=[],
        vision_detections=[],
    )
    findings = evaluate(ctx, RULES)
    assert not any(COMPOUND in f.title.lower() for f in findings)


def test_voice_alone_no_compound() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={},
        readings={},
        permits=[_permit()],
        voice_events=[_voice()],
        vision_detections=[],
    )
    findings = evaluate(ctx, RULES)
    assert not any(COMPOUND in f.title.lower() for f in findings)


def test_vision_alone_no_compound() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={},
        readings={},
        permits=[_permit()],
        voice_events=[],
        vision_detections=[_vision()],
    )
    findings = evaluate(ctx, RULES)
    assert not any(COMPOUND in f.title.lower() for f in findings)
