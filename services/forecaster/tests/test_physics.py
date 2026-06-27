"""Forecaster behaviour: bands not points, and honest UNKNOWN when it can't see."""

from verge_forecaster import forecast
from verge_schema.enums import EstimateQuality, LeadTimeBand


def _ramp(start: float, per_min: float, n: int, step_s: float = 30.0) -> list[tuple[float, float]]:
    return [(i * step_s, start + per_min * (i * step_s / 60.0)) for i in range(n)]


def test_steady_rise_lands_in_near_band() -> None:
    # 60 -> threshold 100, rising 1.0/min => ~40 min => NEAR (15-45)
    samples = _ramp(60.0, 1.0, n=10)
    f = forecast(samples, threshold=100.0)
    assert f.band == LeadTimeBand.NEAR
    assert f.quality == EstimateQuality.HIGH
    assert 30 <= (f.eta_min or 0) <= 45


def test_fast_rise_is_imminent() -> None:
    samples = _ramp(95.0, 5.0, n=10)  # 5/min, 5 to go => ~1 min
    f = forecast(samples, threshold=100.0)
    assert f.band == LeadTimeBand.IMMINENT


def test_degraded_sensor_suppresses_estimate() -> None:
    samples = _ramp(60.0, 1.0, n=10)
    f = forecast(samples, threshold=100.0, degraded=True)
    assert f.band == LeadTimeBand.UNKNOWN
    assert f.quality == EstimateQuality.SUPPRESSED
    assert f.eta_min is None


def test_insufficient_samples_is_unknown() -> None:
    f = forecast([(0.0, 10.0), (1.0, 11.0)], threshold=100.0)
    assert f.band == LeadTimeBand.UNKNOWN
    assert f.quality == EstimateQuality.LOW


def test_not_approaching_is_watch_not_a_number() -> None:
    flat = [(i * 30.0, 50.0) for i in range(10)]
    f = forecast(flat, threshold=100.0)
    assert f.band == LeadTimeBand.WATCH
    assert f.eta_min is None


def test_never_emits_point_estimate_as_band() -> None:
    # The contract: callers consume `band`, never eta_min, for display.
    f = forecast(_ramp(60.0, 1.0, n=10), threshold=100.0)
    assert f.band in set(LeadTimeBand)
