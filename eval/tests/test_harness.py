"""The harness must reproduce the headline: Verge beats every baseline on lead."""

import pytest

from eval.harness import run_incident
from eval.runtime import REPLAYS

ALL_REPLAYS = sorted(
    p.name for p in REPLAYS.iterdir() if (p / "ground-truth.json").exists()
)


def test_all_four_replays_present() -> None:
    assert {"vizag-2025-01", "bp-texas-city-2005", "jaipur-ioc-2009",
            "synthetic-nearmiss-01"} <= set(ALL_REPLAYS)


@pytest.mark.parametrize("incident", ALL_REPLAYS)
def test_verge_beats_every_baseline(incident: str) -> None:
    r = run_incident(incident)
    verge = r["verge"]["leadMin"]
    assert verge is not None and verge > 15, "Verge should have meaningful lead"
    assert r["verge"]["band"] in {"NEAR", "IMMINENT"}

    # Verge's lead must exceed each baseline (silent baselines count as -inf).
    for b in ("b0", "b1", "b2"):
        lead = r[b]["leadMin"]
        baseline_lead = float("-inf") if lead is None else lead
        assert verge > baseline_lead, f"{incident}: Verge must beat {b}"


def test_fpr_is_measured_from_feedback() -> None:
    r = run_incident("vizag-2025-01")
    assert r["fpr"] == 0.2  # 1 false-alarm of 5 seed feedback rows
