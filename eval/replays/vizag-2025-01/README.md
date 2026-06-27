# Replay: vizag-2025-01

**Reconstruction, not ground truth.** Public reports (The Wire investigation,
public DGFASLI summary) give a narrative timeline, *not* per-sensor time-series.
`generate.py` encodes documented synthesis assumptions and emits a defensible
event stream. This is a regression test and a demo — **not** unbiased proof
(spec §10). The first unbiased number comes from a pilot plant's own history.

## Files

| File | What |
|------|------|
| `generate.py` | Deterministic generator (the documented synthesis) |
| `events.jsonl` | Canonical event stream (readings, permit, shift) |
| `ground-truth.json` | Annotated breach time, thresholds, expected convergence |
| `feedback.jsonl` | Synthetic operator feedback seeding the pre-pilot FPR |

## The reconstructed timeline

- **06:40** hot-work permit `PW-2025-0142` opened in zone B-04
- **06:42–07:00** shift changeover (handover blind spot)
- **06:38–06:42** LEL-04 injected `stale` for 4 min (exercises the health plane)
- LEL-04 drifts up from ~80 %LEL, accelerating, **breaching 100 %LEL at ~07:05**

## Regenerate

```bash
python eval/replays/vizag-2025-01/generate.py
python -m eval.harness --incident vizag-2025-01
```

Verge fires the three-way convergence (permit ∩ rising gas ∩ changeover) in the
`NEAR` band well before any single-sensor baseline — which is the whole point.
