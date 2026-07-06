"""Tests for the shared replay runtime (eval/runtime.py)."""

from eval.runtime import band_calibrated, load_replay, run_verge_stream
from verge_schema.enums import LeadTimeBand


def test_load_replay_vizag_events_sorted() -> None:
    gt, events = load_replay("vizag-2025-01")
    assert gt["zoneId"] == "B-04"
    assert events
    assert events == sorted(events, key=lambda e: e["ts"])


def test_run_verge_stream_matches_tick_path() -> None:
    gt, events = load_replay("vizag-2025-01")
    ts, band = run_verge_stream(gt, events)
    assert ts is not None
    assert band in {LeadTimeBand.NEAR, LeadTimeBand.IMMINENT}


def test_band_calibrated_near_window() -> None:
    assert band_calibrated(LeadTimeBand.NEAR, 23.0) is True
    assert band_calibrated(LeadTimeBand.NEAR, 10.0) is False
    assert band_calibrated(LeadTimeBand.UNKNOWN, 20.0) is None
