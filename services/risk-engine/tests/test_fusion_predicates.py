"""Phase 2 fusion predicates — voice, vision, maintenance, generalised sensor."""

from datetime import UTC, datetime, timedelta

from verge_risk import STARTER_RULES, evaluate, load_rules
from verge_risk.context import OpenCapa, RiskContext
from verge_schema.core import MaintenanceOrder, Permit, Reading, Sensor
from verge_schema.events import VisionDetection, VoiceEvent

NOW = datetime(2025, 1, 13, 6, 44, tzinfo=UTC)
RULES = load_rules(STARTER_RULES)


def test_hot_work_voice_gas_smell_fires() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={},
        readings={},
        permits=[
            Permit(
                permit_id="PW-0142",
                kind="hot-work",
                zone_id="B-04",
                valid_from=NOW - timedelta(hours=1),
                valid_to=NOW + timedelta(hours=1),
            )
        ],
        voice_events=[
            VoiceEvent(
                event_id="VE-1",
                ts=NOW - timedelta(minutes=2),
                transcript="gas smell near battery B-04",
                zone_id="B-04",
                hazards=["gas", "smell"],
                source="radio",
            )
        ],
    )
    findings = evaluate(ctx, RULES)
    assert any("radio-reported gas" in f.title.lower() for f in findings)
    hit = next(f for f in findings if "radio-reported gas" in f.title.lower())
    assert any(s.kind == "voice" for s in hit.contributing_signals)


def test_sensor_near_threshold_alias_matches_gas() -> None:
    sensor = Sensor(
        sensor_id="LEL-04",
        kind="gas-lel",
        unit="%LEL",
        zone_id="B-04",
        expected_cadence_s=1.0,
        plausible_min=0.0,
        plausible_max=100.0,
    )
    vals = [90 + i for i in range(6)]
    reads = [
        Reading(
            sensor_id="LEL-04",
            ts=NOW - timedelta(seconds=(len(vals) - 1 - i) * 30),
            value=float(v),
        )
        for i, v in enumerate(vals)
    ]
    ctx = RiskContext(
        now=NOW,
        sensors={"LEL-04": sensor},
        readings={"LEL-04": reads},
        permits=[
            Permit(
                permit_id="PW-0142",
                kind="hot-work",
                zone_id="B-04",
                valid_from=NOW - timedelta(hours=1),
                valid_to=NOW + timedelta(hours=1),
            )
        ],
        thresholds={"gas-lel": 100.0},
        worker_zones={"W-field-1": "B-04"},
    )
    findings = evaluate(ctx, RULES)
    assert any("worker present" in f.title.lower() for f in findings)


def test_vision_ppe_with_hot_work() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={},
        readings={},
        permits=[
            Permit(
                permit_id="PW-0142",
                kind="hot-work",
                zone_id="B-04",
                valid_from=NOW - timedelta(hours=1),
                valid_to=NOW + timedelta(hours=1),
            )
        ],
        vision_detections=[
            VisionDetection(
                detection_id="VD-1",
                ts=NOW - timedelta(seconds=20),
                camera_id="CAM-B04",
                zone_id="B-04",
                label="ppe-missing",
                confidence=0.81,
            )
        ],
    )
    findings = evaluate(ctx, RULES)
    assert any("ppe" in f.title.lower() for f in findings)


def test_maintenance_open_with_vibration() -> None:
    sensor = Sensor(
        sensor_id="VIB-3",
        kind="vibration",
        unit="mm/s",
        zone_id="B-04",
        equipment_id="P-3",
        expected_cadence_s=1.0,
        plausible_min=0.0,
        plausible_max=100.0,
    )
    reads = [
        Reading(sensor_id="VIB-3", ts=NOW - timedelta(seconds=30), value=9.0),
        Reading(sensor_id="VIB-3", ts=NOW, value=9.2),
    ]
    ctx = RiskContext(
        now=NOW,
        sensors={"VIB-3": sensor},
        readings={"VIB-3": reads},
        thresholds={"vibration": 10.0},
        maintenance_orders=[
            MaintenanceOrder(
                order_id="MO-77",
                equipment_id="P-3",
                state="in-progress",
                opened_at=NOW - timedelta(hours=2),
                zone_id="B-04",
            )
        ],
    )
    findings = evaluate(ctx, RULES)
    assert any("maintenance" in f.title.lower() for f in findings)


def test_adjacent_permit_hot_work_confined() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={},
        readings={},
        permits=[
            Permit(
                permit_id="PW-HW",
                kind="hot-work",
                zone_id="B-04",
                valid_from=NOW - timedelta(hours=1),
                valid_to=NOW + timedelta(hours=1),
            ),
            Permit(
                permit_id="PW-CS",
                kind="confined-space",
                zone_id="B-05",
                valid_from=NOW - timedelta(hours=1),
                valid_to=NOW + timedelta(hours=1),
            ),
        ],
        zone_adjacency={"B-04": {"B-05"}, "B-05": {"B-04"}},
    )
    findings = evaluate(ctx, RULES)
    assert any("adjacent" in f.title.lower() for f in findings)


def test_open_capa_with_hot_work() -> None:
    ctx = RiskContext(
        now=NOW,
        sensors={},
        readings={},
        permits=[
            Permit(
                permit_id="PW-HW",
                kind="hot-work",
                zone_id="B-04",
                valid_from=NOW - timedelta(hours=1),
                valid_to=NOW + timedelta(hours=1),
            )
        ],
        open_capas=[
            OpenCapa(
                action_id="CA-1",
                state="open",
                zone_id="B-04",
                title="Fix LEL sensor calibration",
            )
        ],
    )
    findings = evaluate(ctx, RULES)
    assert any("capa" in f.title.lower() for f in findings)
