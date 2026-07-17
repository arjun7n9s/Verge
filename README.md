# Verge

**Industrial intelligence — live risk + living knowledge for zero-harm operations.**

> *"Verge sees it before the threshold — and remembers what the plant already knows."*

At Visakhapatnam Steel Plant (Jan 2025), eight workers died even though gas
detectors, permit-to-work controls, and SCADA were all *functioning*. The
warning signals existed in the data. **No intelligence layer connected those
readings to a decision in time.** Verge is that layer.

Verge fuses gas/IoT, SCADA, permit-to-work, maintenance, shift logs, and CCTV
into one risk picture; detects dangerous *combinations* no single sensor flags;
predicts **lead time** to a threshold breach as a band (not a fake-precise
point estimate); and closes the loop with cited, hash-chained, regulator-ready
evidence — all able to run **inside an air-gapped plant network**.

## Design principles

- **P1 — Fail-operational safety core.** Detection → alert → evacuate runs on
  deterministic rules + classic ML, on-prem, with zero dependency on any LLM.
- **P2 — Open-source / sovereign by default.** Swappable LLM provider.
- **P3 — Source lineage end-to-end.** Every finding links to its raw evidence.
- **P4 — Honest uncertainty and sustained operator trust.** Alert fatigue is a
  first-class concern; a muted system has a 100% false-negative rate.
- **P5 — Eval-driven, replay-provable.** Every claim is reproduced by a harness.
- **P6 — Immutable, signed audit.** Append-only, hash-chained, attributable.
- **P7 — Edge-first ingestion.**
- **P8 — Decision support, not automation.** The operator is the safety interlock.

## Monorepo layout

| Path | What |
|------|------|
| `packages/schema` | Canonical data model (Pydantic + generated TS types) |
| `packages/audit` | Hash-chained, append-only audit library |
| `packages/llm` | `LLMProvider` abstraction (aimlapi ↔ on-prem Ollama/vLLM) |
| `packages/mlops` | Model registry (shadow/canary/production) + PSI drift detection (§14) |
| `packages/contracts` | Versioned data contracts / schema registry for canonical events (§14) |
| `services/edge-gateway` | OPC-UA + MQTT ingest → stream bus |
| `services/risk-engine` | Compound Risk Engine + sensor-health plane (LLM-independent) |
| `services/forecaster` | Rate-based lead-time **bands** |
| `services/orchestrator` | Advisory response — alerts, evidence packs, report drafts (P8) |
| `services/permit` | Digital permit-to-work + SIMOPS spatial-temporal conflict detection |
| `services/twin` | Plant digital twin — zones, adjacency, per-sensor thresholds, **commissioning** (§14.5) |
| `services/compliance` | OISD/Factory Act/DGMS gap detection + hash-chained evidence packs (§5) |
| `services/vision` | PPE/person/zone CV detector plane — degraded-by-default, feeds `frame` lineage (§5) |
| `services/connectors` | Integration hub — historian (PI/PHD) / CMMS (SAP/Maximo) / VMS connectors → canonical events (§14) |
| `services/api` | FastAPI gateway, SSE/WebSocket fan-out, durable store, `/metrics` for plant IT (§14.6) |
| `apps/console` | Operator console (React + Vite + MapLibre/deck.gl) |
| `eval` | Replay-provable eval harness + incident datasets |
| `sims` | SCADA/MQTT simulators emitting realistic event streams |
| `deploy` | Docker Compose (Redpanda, Postgres/PostGIS, TimescaleDB, Neo4j, MinIO, Keycloak) |
| `cli` | The `verge` CLI |
| `docs` | Product & architecture spec |

## Quickstart

```bash
make install   # uv sync (Python workspace) + pnpm install (console)
make up        # bring up infra (docker compose)
make seed      # (re)generate the Vizag replay dataset
make dev       # run api + console
make eval      # run the replay harness vs. baselines B0/B1/B2
make demo-h1   # Horizon-1 tour: commission → compliance → models → ingest|validate
make test      # uv run pytest (whole workspace)
```

**The live path** (sims → risk-engine → API → console), no broker needed. The
engine runs gas rules **and** SIMOPS permit conflicts, resolved against the
plant model (twin):

```bash
# gas convergence — findings print as they fire
uv run verge sim --scenario vizag-like | uv run python -m verge_risk

# SIMOPS — hot-work + confined-space in adjacent zones (compound, no single alarm)
uv run verge sim --scenario simops-demo | uv run python -m verge_risk

# integration hub (§14) — historian + CMMS data → the same engine
uv run verge ingest --demo cmms; uv run verge ingest --demo historian | uv run python -m verge_risk

# shadow mode (§14.5): run alongside the existing alarm system, tag don't alert
uv run verge sim --scenario vizag-like | uv run python -m verge_risk --shadow

# ...and feed the live console (Live / Shadow toggle in the topbar)
uv run verge sim --scenario vizag-like | uv run python -m verge_risk --post http://localhost:8000
```

In production the engine consumes the same canonical events from Redpanda
(`python -m verge_risk --redpanda localhost:19092 --topic verge.events`).

**Commissioning a plant** (§14.5 — the six-step, day-1 onboarding + the sales
artifact). Runs dependency-free, so it works on an air-gapped OT box:

```bash
verge commission                       # full 6-step dry-run on the Vizag demo plant
verge plant import --file zones.geojson --name my-plant --out my-plant.yaml
verge sensor map   --csv sensors.csv --layout zones.geojson
verge rules adopt                      # adopt the OISD starter rule library
verge compliance                       # OISD/Factory Act gap report + evidence pack
```

See [`docs/commissioning.md`](docs/commissioning.md) and
[`docs/operations.md`](docs/operations.md).

**Plant IT** scrapes `GET /metrics` (Prometheus) and `GET /api/ops/status` — a
day-2 surface distinct from the operator console (§14.6).

See [`docs/Verge.md`](docs/Verge.md) for the full product & architecture spec.  
See [`docs/PRODUCT_AUDIT_AND_ROADMAP.md`](docs/PRODUCT_AUDIT_AND_ROADMAP.md) for the dual-wedge product audit and summit roadmap.  
See [`docs/PHASED_BUILD_PLAN.md`](docs/PHASED_BUILD_PLAN.md) for phase-by-phase build detail, OSS/paid stack, and usefulness DoDs.

## Status

v0.3 design spec → Horizon 0 scaffold. Every quantitative figure in the docs is
a **TARGET**, not a measured result, until the eval harness (`eval/`) reproduces
it. No number ships in a deck until the harness can reproduce it on demand.

## License

Apache-2.0. See [LICENSE](LICENSE).
