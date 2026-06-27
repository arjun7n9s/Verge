"""The engine must catch the Vizag-style three-way convergence — and stay quiet
when the legs don't co-occur — and down-weight on degraded sensors."""

from datetime import datetime, timedelta, timezone

from verge_risk import STARTER_RULES, evaluate, load_rules
from verge_risk.context import RiskContext
from verge_schema.core import Permit, Reading, Sensor
from verge_schema.enums import EstimateQuality, LeadTimeBand

NOW = datetime(2025, 1, 13, 6, 44, tzinfo=timezone.utc)
RULES = load_rules(STARTER_RULES)


def _gas_sensor(stuck: bool = False) -> Sensor:
    return Sensor(
        sensor_id="LEL-04", kind="gas-lel", unit="%LEL", zone_id="B-04",
        expected_cadence_s=1.0, plausible_min=0.0, plausible_max=100.0,
    )


def _rising_lel(stuck: bool = False) -> list[Reading]:
    # rising toward the 100 %LEL alarm; ~1.0 %/min over 10 samples (30s apart)
    vals = [85.0] * 10 if stuck else [85 + 0.5 * i for i in range(10)]
    n = len(vals)
    return [
        Reading(sensor_id="LEL-04", ts=NOW - timedelta(seconds=(n - 1 - i) * 30), value=v)
        for i, v in enumerate(vals)
    ]


def _ctx(*, permit: bool, changeover: bool, stuck: bool = False) -> RiskContext:
    permits = []
    if permit:
        permits = [
            Permit(
                permit_id="PW-2025-0142", kind="hot-work", zone_id="B-04",
                valid_from=NOW - timedelta(hours=1), valid_to=NOW + timedelta(hours=1),
            )
        ]
    return RiskContext(
        now=NOW,
        sensors={"LEL-04": _gas_sensor()},
        readings={"LEL-04": _rising_lel(stuck=stuck)},
        permits=permits,
        thresholds={"gas-lel": 100.0},
        in_changeover=changeover,
    )


def test_convergence_fires_critical_with_band() -> None:
    findings = evaluate(_ctx(permit=True, changeover=True), RULES)
    crit = [f for f in findings if "changeover" in f.title.lower()]
    assert crit, "the three-way convergence rule should fire"
    f = crit[0]
    assert f.confidence >= 0.8
    assert f.lead_time_band in {LeadTimeBand.NEAR, LeadTimeBand.IMMINENT, LeadTimeBand.WATCH}
    assert any(s.kind == "permit" for s in f.contributing_signals)
    assert f.counterfactual and "PW-2025-0142" in f.counterfactual


def test_no_permit_no_critical_convergence() -> None:
    findings = evaluate(_ctx(permit=False, changeover=True), RULES)
    titles = [f.title.lower() for f in findings]
    assert not any("hot work" in t for t in titles)


def test_degraded_sensor_downweights_and_suppresses_band() -> None:
    findings = evaluate(_ctx(permit=True, changeover=True, stuck=True), RULES)
    crit = [f for f in findings if "changeover" in f.title.lower()]
    assert crit
    f = crit[0]
    assert f.confidence_degraded is True
    assert "LEL-04" in f.confidence_degraded_by
    assert f.estimate_quality == EstimateQuality.SUPPRESSED
    assert f.lead_time_band == LeadTimeBand.UNKNOWN


def test_lineage_present_on_every_finding() -> None:
    for f in evaluate(_ctx(permit=True, changeover=True), RULES):
        assert f.lineage, "every finding must carry source lineage (P3)"
