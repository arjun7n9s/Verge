# Architecture

Five planes (spec §2). Data flows up; the **safety core is LLM-independent** (P1).

```
①  EDGE / INGESTION   OPC-UA, MQTT, RTSP, file/DB  ──┐  services/edge-gateway
                       normalize + store-and-forward  │
②  STREAM BUS         Redpanda (canonical events)  ◄──┘  deploy/
③  DATA PLANE         TimescaleDB · Postgres/PostGIS · Neo4j · pgvector · MinIO
④  INTELLIGENCE       risk-engine · forecaster · rag · orchestrator · audit
                       └─ LLMProvider (aimlapi ↔ Ollama/vLLM)   packages/llm
⑤  APPLICATION        FastAPI gateway (SSE/WS) · console · alerting
```

## Where the spec lives in code

| Spec | Code |
|------|------|
| §4.1 Compound Risk Engine | `services/risk-engine/verge_risk/engine.py` |
| §4.2 Lead-Time Forecaster | `services/forecaster/verge_forecaster/physics.py` |
| §4.4 Emergency Response Orchestrator | `services/orchestrator/` (advisory; `respond()`) |
| §4.5 Finding lifecycle | `packages/schema/verge_schema/lifecycle.py` |
| §4.6 Alert fatigue (feedback, FPR) | `services/api` store + `FindingFeedback` |
| §4.7 Sensor-health plane | `services/risk-engine/verge_risk/health.py` |
| §5 Pillar 3 — Plant digital twin | `services/twin/verge_twin/plant.py` |
| §5 Pillar 4 — SIMOPS permit conflicts | `services/permit/verge_permit/conflicts.py` |
| §5 — Vision detector plane (PPE/person/zone) | `services/vision/verge_vision/detect.py` |
| §5 — Compliance gap detection + evidence packs | `services/compliance/verge_compliance/` |
| §14.5 Commissioning workflow (6 steps) | `services/twin/verge_twin/commission.py` + `cli/verge_cli/commission.py` |
| §14.5 Layout geometry (dependency-free) | `services/twin/verge_twin/geometry.py` |
| §14.6 Day-2 operability (plant-IT surface) | `services/api/verge_api/ops.py` + `/metrics` |
| §14 Phase 3 — Incident report generator | `services/compliance/verge_compliance/incident_report.py` |
| §14 Phase 4 — Integration hub connectors | `services/connectors/verge_connectors/` |
| §14 Phase 4 — Model registry + drift (MLOps) | `packages/mlops/verge_mlops/` |
| §14 Phase 4 — Schema registry / data contracts | `packages/contracts/verge_contracts/` |
| §4.4 Alert dispatch (operator-gated, P8) | `services/orchestrator/verge_orchestrator/dispatch.py` |
| §6 Safety Rules DSL | `services/risk-engine/verge_risk/rules.py` + `rules/*.yaml` |
| §14.5 Shadow mode | `RiskFinding.shadow` + `run_stream(shadow=)` + `/api/findings?shadow=` |
| Durable store (P6) | `services/api/verge_api/{store_base,store,sql_store,db,factory}.py` |
| §10 Eval harness + baselines | `eval/harness.py`, `eval/baselines/` |
| §10.6 Graceful degradation | LLM `degraded`, edge `StoreAndForward`, `/health` |
| P6 Hash-chained audit | `packages/audit/verge_audit/chain.py` |
| P3 Source lineage | `RiskFinding.lineage` + `contributingSignals[]` |

## Data flow (one finding)

1. Sensors/permits/shift → edge-gateway normalizes → Redpanda.
2. `risk-engine` builds a `RiskContext` snapshot; the Safety Rules DSL fires on a
   zone; each matched predicate adds a `ContributingSignal` (lineage).
3. `forecaster` projects a lead-time **band**; the sensor-health plane may
   down-weight confidence and **suppress** the band on degraded inputs.
4. A `RiskFinding` is created (state `new`) and hash-chained into the audit.
5. The operator works it through the lifecycle; every transition + feedback is
   another hash-chained `AuditEntry`.
6. The eval harness replays all of the above and proves the lead-time edge vs.
   B0/B1/B2 — the same engine, no special-casing.

## The live runtime (`run_stream`)

The streaming runner composes detectors over one event stream: the gas rules
(risk-engine) **plus** injected detectors like SIMOPS permit conflicts (permit),
resolved against the plant model (twin) for thresholds and zone adjacency.
risk-engine stays dependency-clean — composition happens in the CLI. Findings
dedup by `(zone, lineage)` so gas and SIMOPS coexist; `shadow=True` tags them for
the §14.5 review surface instead of surfacing live alerts.

## Persistence

The API depends only on `StoreProtocol`. `InMemoryStore` (default; dev/tests/
demo) and `SqlStore` (durable) are interchangeable, proven by a shared contract
test. `SqlStore` uses SQLAlchemy Core with dialect-agnostic types, so the same
code runs on SQLite (tests, no Docker) and Postgres (`VERGE_STORE=sql`,
`VERGE_DB_URL=postgresql+psycopg://...`). The audit chain is the durable record;
on startup it is rebuilt from the persisted rows and **re-verified** — findings,
feedback, and the hash-chained audit survive a restart, and a tampered audit row
is rejected on load (P6, §10.6, §14.6). The store seeds only when empty.

## The one rule that shapes everything

The detection → alert path must run with **no LLM and no cloud** (P1). The
`LLMProvider` only ever powers narrative/explanation, and it **degrades, never
raises** into the safety path. If you find the safety core importing `verge_llm`
for anything load-bearing, that's a bug.
