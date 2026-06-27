"""The harness must reproduce the headline: Verge beats every baseline on lead."""

import eval._paths  # noqa: F401
from eval.harness import run_incident


def test_vizag_verge_beats_baselines() -> None:
    r = run_incident("vizag-2025-01")
    verge = r["verge"]["leadMin"]
    assert verge is not None and verge > 15, "Verge should have meaningful lead"
    assert r["verge"]["band"] in {"NEAR", "IMMINENT"}

    # Verge's lead must exceed each baseline (silent baselines count as -inf).
    for b in ("b0", "b1", "b2"):
        lead = r[b]["leadMin"]
        baseline_lead = float("-inf") if lead is None else lead
        assert verge > baseline_lead, f"Verge must beat {b}"


def test_fpr_is_measured_from_feedback() -> None:
    r = run_incident("vizag-2025-01")
    assert r["fpr"] == 0.2  # 1 false-alarm of 5 seed feedback rows
