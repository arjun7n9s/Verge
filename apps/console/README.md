# @verge/console

Operator console (spec §2 plane 5, §11). React + Vite + TypeScript, typed by the
shared `@verge/schema` package.

```bash
pnpm install            # from repo root (workspace)
make api                # start the gateway on :8000 (separate shell)
pnpm --filter @verge/console dev   # http://localhost:5173
```

The console is the operator's **working surface** (spec §4.5): findings as a
board by lifecycle state, not a notification feed. It shows:

- the always-visible **sensor-health ribbon** + degradation badges (§4.7, §10.6)
- **lead-time band** per finding (IMMINENT/NEAR/WATCH/UNKNOWN), never a fake point
- **source-lineage chips** on every card (P3)
- the **counterfactual** ("risk drops to LOW if …")
- acknowledge / feedback actions that drive the lifecycle + the measured FPR

Design direction: "Linear meets Palantir Foundry" — neutral graphite/ink, a
single accent for risk, dense data, no glassmorphism, no emoji-as-UI.
