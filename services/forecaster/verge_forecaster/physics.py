"""v1 rate-based lead-time estimation.

Fit a line to the recent window of (t_seconds, value); project to threshold;
bucket minutes-to-threshold into a band. estimateQuality is derived from the
fit (R^2), the sample count, and whether the trajectory is accelerating toward
the limit. Pure stdlib — no numpy — so it runs anywhere the safety core runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from verge_schema.enums import BAND_BOUNDS_MIN, EstimateQuality, LeadTimeBand

MIN_SAMPLES = 4


@dataclass(frozen=True)
class Forecast:
    band: LeadTimeBand
    eta_min: float | None  # internal/debug only; the UI shows the band
    basis: str
    quality: EstimateQuality


def _linfit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Least-squares slope, intercept, R^2."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return 0.0, my, 0.0
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r2


def _band_for(eta_min: float) -> LeadTimeBand:
    for band, (lo, hi) in BAND_BOUNDS_MIN.items():
        if band is LeadTimeBand.UNKNOWN:
            continue
        lo = lo if lo is not None else float("-inf")
        hi = hi if hi is not None else float("inf")
        if lo <= eta_min < hi:
            return band
    return LeadTimeBand.WATCH


def forecast(
    samples: list[tuple[float, float]],
    threshold: float,
    *,
    degraded: bool = False,
    rising_is_bad: bool = True,
) -> Forecast:
    """`samples` = [(t_seconds, value), ...] ascending. `threshold` is the limit.

    Returns a band + estimateQuality. When a contributing sensor is degraded
    (spec §4.7) we refuse to emit a band: quality=suppressed, band=UNKNOWN.
    """
    if degraded:
        return Forecast(LeadTimeBand.UNKNOWN, None, "degraded contributing sensor", EstimateQuality.SUPPRESSED)

    if len(samples) < MIN_SAMPLES:
        return Forecast(LeadTimeBand.UNKNOWN, None, "insufficient samples", EstimateQuality.LOW)

    xs = [t for t, _ in samples]
    ys = [v for _, v in samples]
    slope, _, r2 = _linfit(xs, ys)  # value units per second
    current = ys[-1]

    # Not approaching the limit in the dangerous direction -> WATCH, not a number.
    approaching = slope > 0 if rising_is_bad else slope < 0
    if not approaching or slope == 0:
        return Forecast(LeadTimeBand.WATCH, None, "no approach to threshold", EstimateQuality.MEDIUM)

    remaining = (threshold - current) if rising_is_bad else (current - threshold)
    if remaining <= 0:
        return Forecast(LeadTimeBand.IMMINENT, 0.0, "already at/over threshold", EstimateQuality.HIGH)

    eta_min = (remaining / abs(slope)) / 60.0
    band = _band_for(eta_min)

    # Quality: good fit + enough samples = high; poor fit = low.
    if r2 >= 0.9 and len(samples) >= 8:
        quality = EstimateQuality.HIGH
    elif r2 >= 0.6:
        quality = EstimateQuality.MEDIUM
    else:
        quality = EstimateQuality.LOW

    basis = f"rate-of-rise {slope * 60:.3g}/min, R^2={r2:.2f}, n={len(samples)}"
    return Forecast(band, round(eta_min, 1), basis, quality)
