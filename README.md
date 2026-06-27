# Verge

**The lead-time intelligence layer for zero-harm industrial operations.**

> *"Verge sees it before the threshold."*

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
| `services/edge-gateway` | OPC-UA + MQTT ingest → stream bus |
| `services/risk-engine` | Compound Risk Engine + sensor-health plane (LLM-independent) |
| `services/forecaster` | Rate-based lead-time **bands** |
| `services/orchestrator` | Advisory response — alerts, evidence packs, report drafts (P8) |
| `services/api` | FastAPI gateway, SSE/WebSocket fan-out |
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
make test      # uv run pytest (whole workspace)
```

**The live path** (sims → risk-engine → API → console), no broker needed:

```bash
# stream a scenario through the engine; findings print as they fire
uv run verge sim --scenario vizag-like | uv run python -m verge_risk

# ...and feed them to the running console
uv run verge sim --scenario vizag-like | uv run python -m verge_risk --post http://localhost:8000
```

In production the engine consumes the same canonical events from Redpanda
(`python -m verge_risk --redpanda localhost:19092 --topic verge.events`).

See [`docs/Verge.md`](docs/Verge.md) for the full product & architecture spec.

## Status

v0.3 design spec → Horizon 0 scaffold. Every quantitative figure in the docs is
a **TARGET**, not a measured result, until the eval harness (`eval/`) reproduces
it. No number ships in a deck until the harness can reproduce it on demand.

## License

Apache-2.0. See [LICENSE](LICENSE).
