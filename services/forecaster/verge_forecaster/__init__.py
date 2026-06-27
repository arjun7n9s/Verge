"""Lead-time forecaster (spec §4.2).

Ships as v1 = rate-based physics: extrapolate rate-of-rise to the threshold and
bucket the result into a *band*. No training data, fully transparent, debuggable.

Hard rules from the spec:
- Output a band (IMMINENT/NEAR/WATCH/UNKNOWN), NEVER a fake-precise point.
- A wrong lead time is worse than none -> when the fit is poor or a contributing
  sensor is degraded, return UNKNOWN with estimateQuality=suppressed and let the
  console show the raw trend instead.
- Lead time is decision-support; no automated action keys off it alone (P8).
"""

from .physics import Forecast, forecast

__all__ = ["Forecast", "forecast"]
__version__ = "0.3.0"
