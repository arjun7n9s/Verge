"""Verge eval harness — replay-provable evidence (spec §10).

The harness replays a reconstructed incident, runs Verge alongside three
baselines (B0 fixed-threshold, B1 rate-of-rise, B2 multi-sensor AND-gate), and
reports who caught what, at which lead-time band, and how far ahead of breach.

Methodological honesty (spec §10): these replays are *reconstructions* from
public narrative reports, not per-sensor ground truth. The harness is a strong
demo and a regression test — not unbiased proof. The first unbiased number comes
from a pilot plant's own history (Horizon 1).
"""
