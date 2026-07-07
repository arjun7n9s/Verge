"""Integration-hub connectors: canonical events + honest degradation (spec §14)."""

from __future__ import annotations

from verge_connectors import (
    CsvCmmsConnector,
    HoneywellPhdConnector,
    MaximoConnector,
    NullConnector,
    PiWebApiConnector,
    connector_from_env,
    demo_cmms,
    demo_historian,
    get_connector,
)


def test_csv_historian_emits_canonical_readings_and_skips_unmapped():
    result = demo_historian().pull()
    assert not result.degraded
    assert result.events
    assert all(e["type"] == "reading" for e in result.events)
    # Every emitted reading resolved a mapped sensor; the unmapped tag was dropped.
    assert {e["sensorId"] for e in result.events} <= {"LEL-04", "CO-04", "LEL-05"}
    assert result.skipped >= 1  # UNMAPPED.TAG.PV
    lel = next(e for e in result.events if e["sensorId"] == "LEL-04")
    assert lel["kind"] == "gas-lel" and lel["zoneId"] == "B-04"


def test_historian_since_filter():
    all_events = demo_historian().pull().events
    later = demo_historian().pull(since="2025-01-14T06:06:00+00:00")
    assert len(later.events) < len(all_events)
    assert all(e["ts"] >= "2025-01-14T06:06:00+00:00" for e in later.events)


def test_csv_cmms_emits_permit_events():
    result = demo_cmms().pull()
    assert not result.degraded
    kinds = {e["kind"] for e in result.events}
    assert {"hot-work", "confined-space", "isolation"} <= kinds
    assert all(e["type"] == "permit" for e in result.events)
    hot = next(e for e in result.events if e["kind"] == "hot-work")
    assert hot["zoneId"] == "B-04" and hot["equipmentId"] == "charging-car-hydraulics"


def test_missing_csv_degrades_not_raises(tmp_path):
    result = CsvCmmsConnector(tmp_path / "nope.csv").pull()
    assert result.degraded and "not found" in result.reason


def test_proprietary_connectors_degrade_without_config():
    for conn in (PiWebApiConnector({}), HoneywellPhdConnector({}), MaximoConnector({})):
        result = conn.pull()
        assert result.degraded
        assert result.events == []
        assert "not configured" in result.reason


def test_proprietary_connector_configured_but_unreachable_is_honest():
    conn = PiWebApiConnector({"VERGE_PI_WEB_API_URL": "https://pi.example/piwebapi"})
    result = conn.pull()
    # Configured but no live host here -> degraded, still no fabricated data.
    assert result.degraded and "unreachable" in result.reason
    assert result.events == []


def test_env_selection_defaults_to_null():
    assert isinstance(connector_from_env({}), NullConnector)
    assert connector_from_env({}).pull().degraded


def test_historian_rejects_non_finite_readings(tmp_path):
    from verge_connectors import CsvHistorianConnector

    csv = "tag,ts,value\nT1,2025-01-14T06:00:00,NaN\nT1,2025-01-14T06:01:00,42.0\n"
    p = tmp_path / "r.csv"
    p.write_text(csv, encoding="utf-8")
    tagmap = {"T1": {"sensorId": "S1", "kind": "gas-lel", "unit": "%LEL", "zoneId": "B-04"}}
    result = CsvHistorianConnector(p, tagmap).pull()
    # NaN row dropped + counted; only the finite reading survives.
    assert [e["value"] for e in result.events] == [42.0]
    assert result.skipped >= 1


def test_historian_tolerates_utf8_bom(tmp_path):
    from verge_connectors import CsvHistorianConnector

    # Excel/Windows exports often prepend a BOM; it must not blank the header.
    p = tmp_path / "bom.csv"
    p.write_bytes(b"\xef\xbb\xbftag,ts,value\nT1,2025-01-14T06:00:00,42.0\n")
    tagmap = {"T1": {"sensorId": "S1", "kind": "gas-lel", "unit": "%LEL", "zoneId": "B-04"}}
    result = CsvHistorianConnector(p, tagmap).pull()
    assert len(result.events) == 1 and result.events[0]["sensorId"] == "S1"


def test_since_filter_compares_instants_not_strings(tmp_path):
    from verge_connectors import CsvHistorianConnector

    # Two readings at the same instant expressed in different offsets: +05:30
    # (00:30 UTC, earlier) and +00:00 (06:00 UTC, later). A lexical compare would
    # order them wrong; instant compare keeps only the one after `since`.
    csv = ("tag,ts,value\n"
           "T1,2025-01-14T06:00:00+05:30,1.0\n"
           "T1,2025-01-14T06:00:00+00:00,2.0\n")
    p = tmp_path / "tz.csv"
    p.write_text(csv, encoding="utf-8")
    tagmap = {"T1": {"sensorId": "S1", "kind": "gas-lel", "unit": "%LEL", "zoneId": "B-04"}}
    result = CsvHistorianConnector(p, tagmap).pull(since="2025-01-14T03:00:00+00:00")
    # Only the 06:00 UTC reading is after 03:00 UTC; the 00:30 UTC one is dropped.
    assert [e["value"] for e in result.events] == [2.0]


def test_get_connector_csv_historian_from_env():
    from verge_connectors.historian import SAMPLES_DIR

    conn = get_connector("csv-historian", {
        "VERGE_HISTORIAN_CSV": str(SAMPLES_DIR / "historian-readings.csv"),
        "VERGE_HISTORIAN_TAGMAP": str(SAMPLES_DIR / "historian-tagmap.json"),
    })
    assert conn.pull().events
