"""Distribution drift detection via the Population Stability Index (spec §14 P4).

Drift is the MLOps early-warning that a model's world has moved out from under
it — the feature (or score) distribution the model sees in production no longer
matches the reference distribution it was validated on. PSI is the standard,
interpretable measure and needs no numeric stack, so it runs anywhere (P2):

    PSI = Σ (actual% − expected%) · ln(actual% / expected%)

Reference-derived quantile bins; a small epsilon floors empty bins so the log is
finite. Conventional severity bands: < 0.10 stable, 0.10–0.25 moderate, ≥ 0.25
significant (retrain/investigate).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_EPS = 1e-6
STABLE = "stable"
MODERATE = "moderate"
SIGNIFICANT = "significant"


def _quantile_edges(values: list[float], bins: int) -> list[float]:
    """Bin edges at evenly spaced quantiles of the reference sample."""
    ordered = sorted(values)
    n = len(ordered)
    edges = [ordered[0]]
    for i in range(1, bins):
        idx = min(n - 1, int(round(i * n / bins)))
        edges.append(ordered[idx])
    edges.append(ordered[-1])
    # De-duplicate collinear edges (degenerate/low-variance references).
    out: list[float] = []
    for e in edges:
        if not out or e > out[-1]:
            out.append(e)
    return out


def _bin_fractions(values: list[float], edges: list[float]) -> list[float]:
    counts = [0] * (len(edges) - 1)
    for v in values:
        placed = False
        for i in range(len(edges) - 1):
            hi = edges[i + 1]
            # last bin is closed on the right so max value lands inside
            if v < hi or (i == len(edges) - 2 and v <= hi):
                counts[i] += 1
                placed = True
                break
        if not placed:  # v beyond the reference range -> nearest edge bin
            counts[0 if v < edges[0] else -1] += 1
    total = sum(counts) or 1
    return [c / total for c in counts]


@dataclass
class DriftResult:
    psi: float
    severity: str
    bins: int
    n_reference: int
    n_current: int

    @property
    def drifted(self) -> bool:
        return self.severity != STABLE

    def to_dict(self) -> dict:
        return {
            "psi": round(self.psi, 4),
            "severity": self.severity,
            "drifted": self.drifted,
            "bins": self.bins,
            "nReference": self.n_reference,
            "nCurrent": self.n_current,
        }


def classify(psi: float) -> str:
    if psi < 0.10:
        return STABLE
    if psi < 0.25:
        return MODERATE
    return SIGNIFICANT


def population_stability_index(
    reference: list[float], current: list[float], *, bins: int = 10
) -> DriftResult:
    """PSI between a reference and a current sample, with a severity band."""
    # Drop non-finite values first: NaN breaks sorting/binning (NaN compares
    # false against everything) and would otherwise yield a bogus "stable"
    # verdict — the worst failure mode for a drift monitor.
    reference = [x for x in reference if math.isfinite(x)]
    current = [x for x in current if math.isfinite(x)]
    if not reference or not current:
        return DriftResult(0.0, STABLE, bins, len(reference), len(current))
    edges = _quantile_edges(reference, bins)
    if len(edges) < 3:  # reference has ~no variance; treat as stable
        return DriftResult(0.0, STABLE, bins, len(reference), len(current))
    exp = _bin_fractions(reference, edges)
    act = _bin_fractions(current, edges)
    psi = 0.0
    for e, a in zip(exp, act, strict=True):
        e = max(e, _EPS)
        a = max(a, _EPS)
        psi += (a - e) * math.log(a / e)
    return DriftResult(psi, classify(psi), len(edges) - 1, len(reference), len(current))
