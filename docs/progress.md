# Dex Progress Log

## 2026-07-06 22:16 IST - Repo orientation and task read

### What I did

- Read the repository root layout and file inventory with `Get-ChildItem -Force` and `rg --files`.
- Checked the working tree with `git status --short`.
- Read the main product and architecture docs:
  - `README.md`
  - `docs/Verge.md`
  - `docs/ARCHITECTURE.md`
  - `docs/dex.md`
  - `docs/WORK.lock`
- Confirmed the user mentioned a Dex folder, but the repo currently has `docs/dex.md`, not `docs/dex/`.
- Read the current API/store implementation:
  - `services/api/verge_api/main.py`
  - `services/api/verge_api/store_base.py`
  - `services/api/verge_api/store.py`
  - `services/api/verge_api/sql_store.py`
  - `services/api/verge_api/factory.py`
  - `services/api/verge_api/seed.py`
  - `services/api/tests/test_api.py`
- Read the core data contracts and audit chain:
  - `packages/schema/verge_schema/core.py`
  - `packages/schema/verge_schema/enums.py`
  - `packages/schema/verge_schema/findings.py`
  - `packages/schema/verge_schema/lifecycle.py`
  - `packages/audit/verge_audit/chain.py`
- Read the safety core, live runner, forecaster, rules, SIMOPS, and eval harness:
  - `services/risk-engine/verge_risk/engine.py`
  - `services/risk-engine/verge_risk/runner.py`
  - `services/risk-engine/verge_risk/rules.py`
  - `services/risk-engine/verge_risk/rules/starter.yaml`
  - `services/forecaster/verge_forecaster/physics.py`
  - `services/permit/verge_permit/conflicts.py`
  - `services/permit/verge_permit/findings.py`
  - `eval/harness.py`
  - `eval/tests/test_harness.py`
- Read supporting integration surfaces:
  - `packages/llm/verge_llm/__init__.py`
  - `packages/llm/verge_llm/providers.py`
  - `services/orchestrator/verge_orchestrator/orchestrate.py`
  - `services/orchestrator/verge_orchestrator/report.py`
  - `services/edge-gateway/verge_edge/normalize.py`
  - `services/twin/verge_twin/plant.py`
  - `cli/verge_cli/cli.py`
  - `Makefile`
  - `deploy/README.md`
- Read the console API contract and board/card surfaces without editing them:
  - `apps/console/src/api.ts`
  - `apps/console/src/App.tsx`
  - `apps/console/src/components/FindingsBoard.tsx`
  - `apps/console/src/components/FindingCard.tsx`
  - `apps/console/README.md`
  - `tests/test_e2e_live_path.py`
- Checked whether Dex-owned code already exists:
  - `packages/memory` does not exist yet.
  - `services/voice` does not exist yet.
  - `services/api/verge_api/routes` did not exist at the time of my check.
- Ran verification:
  - `uv run pytest -q` passed 103 tests.
  - `uv run ruff check .` passed.
- Added a temporary lock line for this log in `docs/WORK.lock` before editing `docs/progress.md`.
- Created this file, `docs/progress.md`, as the requested Dex activity log.

### What I learned about the product

- Verge is a lead-time intelligence layer for industrial safety, focused on seeing compound risk before a threshold breach.
- The core wedge is: compound risk detection, lead-time bands, source lineage, and replay-provable evals.
- The safety path must remain deterministic, on-prem, and LLM-free. LLM/cloud components are narrative/context helpers only and must degrade cleanly.
- The current repo is a Python/TypeScript monorepo with:
  - canonical schema in `packages/schema`
  - hash-chained audit in `packages/audit`
  - LLM abstraction in `packages/llm`
  - deterministic safety core in `services/risk-engine`
  - rate-based lead-time bands in `services/forecaster`
  - permit/SIMOPS detection in `services/permit`
  - plant twin in `services/twin`
  - FastAPI gateway in `services/api`
  - React console in `apps/console`
  - replay harness and datasets in `eval`
  - simulators in `sims`
  - deployment scaffold in `deploy`
  - CLI in `cli`

### Current progress I observed

- API exists and currently lives mostly in `services/api/verge_api/main.py`.
- The API already supports:
  - `/health`
  - `/api/findings`
  - `/api/findings/{finding_id}`
  - finding ingest
  - lifecycle transitions
  - feedback/FPR
  - orchestrator response drafts
  - sensor ribbon
  - audit reads
  - SSE stream snapshots
- Store abstraction exists through `StoreProtocol`, with in-memory and SQL implementations.
- Audit chain is implemented and tested for tamper detection.
- Finding lifecycle state machine is implemented in schema code and enforced by the API/store.
- Risk engine evaluates starter rules over a `RiskContext`, emits `RiskFinding` objects, carries lineage, downweights degraded sensors, and calls the forecaster.
- Forecaster uses transparent rate-of-rise physics and emits bands, not point estimates.
- Live runner consumes canonical event dictionaries, accumulates rolling sensor windows, evaluates rules, injects extra detectors, deduplicates by zone plus lineage, and supports shadow mode.
- Eval harness replays four incident datasets and compares Verge against B0 fixed threshold, B1 rate-of-rise, and B2 AND-gate.
- Console is already wired to current findings, transitions, feedback, shadow mode, and sensor ribbon. It is not yet wired to Dex memory context.
- Dex-owned memory and voice packages/routes have not landed yet.

### Dex task understanding

Per `docs/dex.md`, Dex owns the backend intelligence layer workstream:

- D1: scaffold `packages/memory` for Cognee Cloud.
- D2: add static seed corpus and idempotent ingest.
- D3: add memory API route `GET /api/findings/{finding_id}/context`.
- D4: scaffold `services/voice` for Speechmatics transcription.
- D5: add voice API routes for transcription and handover.
- D6: optional shift handover report.
- D7: optional MinIO manifest stub.
- D8: READMEs, curl examples, and Dex demo docs.

Important constraints:

- Do not edit `apps/console/**`.
- Do not edit `services/risk-engine/**`, `eval/**`, `services/twin/**`, or `deploy/**`.
- Do not edit `services/api/verge_api/store*.py`.
- Ask or lock before touching shared files like `services/api/verge_api/main.py`, root `pyproject.toml`, or `packages/schema/**`.
- New API route files under `services/api/verge_api/routes/**` are Dex-owned.
- Cloud/API failures or missing credentials must return degraded responses, not 500s and not fake success.
- Tests must mock network calls.

### Active locks observed

At the time of logging, `docs/WORK.lock` had active non-Dex lines for:

- `eval/harness.py eval/runtime.py` - M2 eval runtime parity
- `services/risk-engine/verge_risk/runner.py` - window kwarg
- `services/twin/verge_twin/export.py` - M5 geojson
- `services/api/verge_api/routes/plant.py` - plant geojson API
- `services/api/verge_api/main.py` - include plant router
- `services/risk-engine/verge_risk/rules/starter.yaml` - M3 rules expand

I did not edit those paths.

### Working tree notes

Pre-existing uncommitted changes were present before I created this log:

- `.env.example`
- `deploy/.env.example`
- `services/risk-engine/verge_risk/runner.py`
- `docs/WORK.lock`
- `docs/dex.md`

I did not modify the env examples, risk-engine runner, console, eval, twin, deploy, schemas, stores, or root workspace config. My intended Dex change for this session is only `docs/progress.md`, plus the temporary lock-line maintenance in `docs/WORK.lock`.

## 2026-07-06 22:20 IST - D1-D3 memory work started

### What I did

- Re-checked `git status --short`, `docs/WORK.lock`, and the Dex-owned paths.
- Confirmed `packages/memory` and `services/voice` still did not exist.
- Confirmed `services/api/verge_api/routes` now exists with the main-team plant route.
- Read the updated `services/api/verge_api/main.py`, `routes/plant.py`, root `pyproject.toml`, and `services/api/pyproject.toml`.
- Checked current Cognee docs before wiring the client:
  - Cognee Cloud uses a tenant base URL and `X-Api-Key`.
  - HTTP endpoints use `/api/v1`.
  - Data flow is `add`, `cognify`, then `search`, with dataset scoping.
- Claimed Dex/shared paths in `docs/WORK.lock`.
- Implemented the D1-D3 memory foundation:
  - `packages/memory/pyproject.toml`
  - `packages/memory/README.md`
  - `packages/memory/verge_memory/client.py`
  - `packages/memory/verge_memory/datasets.py`
  - `packages/memory/verge_memory/ingest.py`
  - `packages/memory/verge_memory/retrieve.py`
  - `packages/memory/verge_memory/corpus/vizag-2025-summary.md`
  - `packages/memory/verge_memory/corpus/oisd-stubs.json`
  - `packages/memory/tests/test_memory.py`
  - `services/api/verge_api/routes/memory.py`
  - `services/api/tests/test_memory_routes.py`
- Registered `verge-memory` in the root workspace and as an API dependency.
- Registered the memory router in `services/api/verge_api/main.py`.

### Notes

- The memory client is degraded-by-default. Missing `VERGE_COGNEE_ENABLED=true`,
  `COGNEE_API_KEY`, or Cognee base URL returns empty arrays with `degraded: true`.
- Tests use `httpx.MockTransport`; no real Cognee network calls are required.
- The route returns a normal 404 for an unknown Verge finding, but Cognee
  unavailability is represented in the response body.
- Targeted memory/API tests passed.
- Full `uv run pytest -q` passed after D1-D3.
- Full `uv run ruff check .` currently fails in non-Dex files that landed during
  the session (`eval/harness.py`, `eval/runtime.py`, `eval/tests/test_runtime.py`,
  and `services/twin/verge_twin/__init__.py`). I did not edit those paths.

## 2026-07-06 22:35 IST - D4-D5 voice work started

### What I did

- Checked current Speechmatics docs before wiring the client:
  - Batch jobs use Bearer auth.
  - Production batch endpoints are region based, e.g. `eu1.asr.api.speechmatics.com`.
  - The REST API exposes `/v2/jobs` and `/v2/jobs/{job_id}/transcript`.
- Added locks for `services/voice`, the voice route, voice tests, and shared API registration files.
- Implemented `verge-voice`:
  - `services/voice/pyproject.toml`
  - `services/voice/README.md`
  - `services/voice/verge_voice/__init__.py`
  - `services/voice/verge_voice/transcribe.py`
  - `services/voice/tests/test_voice.py`
- Implemented API voice routes:
  - `POST /api/voice/transcribe`
  - `POST /api/voice/handover`
- Registered `verge-voice` in the root workspace and API dependencies.
- Added `python-multipart` for FastAPI upload handling.
- Registered the voice router in `services/api/verge_api/main.py`.

### Notes

- Missing `SPEECHMATICS_API_KEY`, empty uploads, timeouts, failed jobs, or HTTP
  failures return `degraded: true`.
- `/api/voice/handover` appends a `voice-handover` audit entry even when the
  speech provider is degraded, so the attempted handover remains hash-chained.

### Verification

- `uv sync` completed after adding `verge-memory`, `verge-voice`, and
  `python-multipart`.
- `uv run pytest packages/memory services/voice services/api/tests/test_memory_routes.py services/api/tests/test_voice_routes.py -q`
  passed 11 tests.
- `uv run ruff check packages/memory services/voice services/api/verge_api/routes/memory.py services/api/verge_api/routes/voice.py services/api/tests/test_memory_routes.py services/api/tests/test_voice_routes.py`
  passed.
- `uv run pytest -q` passed the full suite.
- `uv run ruff check .` still fails in non-Dex files:
  - `eval/harness.py`
  - `eval/runtime.py`
  - `eval/tests/test_runtime.py`
  - `services/twin/verge_twin/__init__.py`

### Files changed by Dex in this pass

- `packages/memory/**`
- `services/voice/**`
- `services/api/verge_api/routes/memory.py`
- `services/api/verge_api/routes/voice.py`
- `services/api/tests/test_memory_routes.py`
- `services/api/tests/test_voice_routes.py`
- `services/api/verge_api/main.py`
- `services/api/pyproject.toml`
- `pyproject.toml`
- `uv.lock`
- `docs/dex.md`
- `docs/progress.md`
- `docs/WORK.lock` for temporary lock bookkeeping

## 2026-07-07 - D9 memory query API

### What I did

- Re-read `docs/dex.md` after the Phase 2 update.
- Chose D9 as the first Phase 2 lane because it stays inside Dex memory/API-route ownership.
- Confirmed active locks did not overlap with the backend memory route work.
- Added `packages/memory/verge_memory/query.py`.
- Added `query_memory(...)` export from `verge_memory`.
- Added `POST /api/memory/query` to `services/api/verge_api/routes/memory.py`.
- Added mocked package and route tests for degraded and successful query paths.
- Updated `packages/memory/README.md` with the free-text query API shape and curl.
- Marked D9 complete in `docs/dex.md`.

### Notes

- The route accepts `{ "query": "...", "findingId": "..." }`.
- `findingId` scopes the query with finding title, zone, and lineage. Unknown
  finding IDs return 404.
- Missing Cognee configuration or Cognee failures return `{ "answer": "",
  "citations": [], "degraded": true }`.

### Verification

- `uv run pytest packages/memory services/api/tests/test_memory_routes.py -q`
  passed 10 tests.
- `uv run ruff check packages/memory services/api/verge_api/routes/memory.py services/api/tests/test_memory_routes.py`
  passed.
- `uv run pytest -q` passed the full suite.
- `uv run ruff check .` passed.

### Files changed by Dex in this pass

- `packages/memory/verge_memory/query.py`
- `packages/memory/verge_memory/__init__.py`
- `packages/memory/tests/test_memory.py`
- `packages/memory/README.md`
- `services/api/verge_api/routes/memory.py`
- `services/api/tests/test_memory_routes.py`
- `docs/dex.md`
- `docs/progress.md`
- `docs/WORK.lock` for temporary lock bookkeeping

## 2026-07-07 - Sprint B Intelligence Platform

### What I did

- Re-read `docs/dex.md` and took Sprint B as a block instead of choosing one task.
- Claimed all Sprint B paths in `docs/WORK.lock`, including the shared API glue needed for the evidence route and feedback hook.
- B1 / D13 Cognee hardening:
  - Added retry/backoff settings to `CogneeClient`.
  - Added `dataset_health()` in `packages/memory/verge_memory/status.py`.
  - Added `GET /api/memory/status`.
- B2 corpus expansion:
  - Added Jaipur and BP Texas City incident summary stubs.
  - Expanded `oisd-stubs.json` to 15+ clauses.
  - Updated corpus loading to ingest all `*-summary.md` files.
- B3 / D12 evidence retrieval:
  - Added `get_evidence_manifest(...)` in `evidence_store.py`.
  - Added `GET /api/evidence/{pack_id}` in `routes/evidence.py`.
  - Registered the evidence router.
- B4 / D11 near-miss voice:
  - Added `services/voice/verge_voice/near_miss.py`.
  - Added `POST /api/voice/near-miss`.
  - Ensured near-miss audit payloads are copied before response mutation so the hash chain remains valid.
- B5 / D14 alert preview:
  - Added `services/voice/verge_voice/alert_preview.py`.
  - Added `POST /api/findings/{id}/alert/preview`.
  - Template fallback returns English and Hindi when LLM output is degraded.
- B6 / D15 integration tests:
  - Added `tests/integration/test_memory_voice_path.py`.
  - Added a Sprint B curl matrix to `packages/memory/README.md`.
- B7 / D10 feedback loop:
  - Added `ingest_feedback(...)` in `packages/memory`.
  - Wired `maybe_ingest_feedback(...)` through `services/api/verge_api/hooks.py`.

### Verification

- `uv sync` completed.
- `uv run pytest packages/memory services/voice services/api/tests/test_memory_routes.py services/api/tests/test_voice_routes.py services/api/tests/test_evidence_routes.py tests/integration/test_memory_voice_path.py -q`
  passed 26 tests.
- `uv run ruff check packages/memory services/voice services/api/verge_api/routes/memory.py services/api/verge_api/routes/voice.py services/api/verge_api/routes/evidence.py services/api/verge_api/evidence_store.py services/api/tests/test_memory_routes.py services/api/tests/test_voice_routes.py services/api/tests/test_evidence_routes.py tests/integration/test_memory_voice_path.py`
  passed.
- `uv run pytest -q` passed the full suite.
- `uv run ruff check .` passed.

### Files changed by Dex in this pass

- `packages/memory/**`
- `services/voice/**`
- `services/api/verge_api/routes/memory.py`
- `services/api/verge_api/routes/voice.py`
- `services/api/verge_api/routes/evidence.py`
- `services/api/verge_api/evidence_store.py`
- `services/api/verge_api/hooks.py`
- `services/api/verge_api/main.py`
- `services/api/tests/test_memory_routes.py`
- `services/api/tests/test_voice_routes.py`
- `services/api/tests/test_evidence_routes.py`
- `tests/integration/test_memory_voice_path.py`
- `docs/dex.md`
- `docs/progress.md`
- `docs/WORK.lock`

## 2026-07-07 - Early Horizon 1 prep (agent / main track)

Long autonomous build run toward Horizon 1 (first-pilot). Baseline was 152 tests
green; ended at 195 green, `ruff check .` clean. Everything local — no commits.

### H1-A · Commissioning workflow (§14.5) — the day-1 Horizon 1 onboarding

- `services/twin/verge_twin/geometry.py` — **dependency-free** planar polygon
  toolkit (area, point-in-polygon, overlap vs. touch, shared-edge adjacency), so
  layout validation runs on an air-gapped box with no GEOS/shapely (P2).
- `services/twin/verge_twin/commission.py` — layout import + validation (overlap
  errors, adjacency **inference**, coverage/gaps, isolated-zone flags) and sensor
  CSV mapping (unassigned sensors flagged + excluded from scoring).
- `cli/verge_cli/commission.py` + new CLI verbs: `verge plant import`,
  `verge sensor map`, `verge rules adopt`, `verge commission` (the full 6-step
  report with dry-run vs. B0/B1/B2 — the persuasive artifact).
- Inferred adjacency **exactly matches** the hand-written demo plant (test).
- Demo inputs: `plants/vizag-zones.geojson` (existing) + new `vizag-sensors.csv`.
- Docs: `docs/commissioning.md`.

### H1-B · Compliance service (§5, Phase 3)

- New `services/compliance` package: `clauses.py` (OISD/Factory Act/DGMS clause
  library as data → capability), `gaps.py` (deterministic, LLM-free gap
  detection over plant model + adopted rules), `evidence.py` (reproducible,
  hash-chained compliance evidence packs — same `canonical_json` as the audit
  chain), `render.py` (regulator-readable markdown).
- Demo plant scores 81% coverage with **honest gaps** (isolation, startup,
  tank-farm — controls a coke-oven plant genuinely lacks).
- API: `GET /api/compliance/report`, `GET /api/compliance/gaps`.
- CLI: `verge compliance`.

### H1-C · Vision detector plane (§5, Phase 2)

- New `services/vision` package: PPE/person/zone-intrusion CV plane,
  **degraded-by-default** (no GPU/model → `degraded: true`, never fabricated).
  Backends: `stub`, `annotations` (deterministic replay, no GPU), lazy
  `ultralytics` (degrades if absent). Detections → `ContributingSignal(kind="frame")`.
- API: `POST /api/vision/detect`; `app.state.vision` env-selected provider.

### H1-D · Plant-IT day-2 operability (§14.6)

- `services/api/verge_api/ops.py` — snapshot (audit integrity, ingest health,
  sensor-health rollup, degradation posture, backup/bundle age, last replay) +
  **dependency-free** Prometheus text exporter.
- `GET /metrics` (Prometheus) and `GET /api/ops/status` (JSON), distinct from the
  operator console. Unmeasured facts are `null`/omitted, never faked (P4).
- Docs: `docs/operations.md`.

### Shared-file / workspace changes

- Root `pyproject.toml` + `conftest.py`: registered `services/compliance`,
  `services/vision`; added `cli` to `testpaths`. `services/api/pyproject.toml`
  and `cli/pyproject.toml`: declared the new deps. `main.py`: registered
  compliance/vision/ops routers, `/metrics`, `app.state.vision`, `started_at`.
- `reading_buffer.py`: added read-only `sensor_count`/`reading_count`/`latest_ts`.
- README, ARCHITECTURE spec-to-code map updated.

## 2026-07-07 - Early Horizon 1 prep, phases E–H (agent / main track)

Continued the long build run. Ended at 225 tests green, `ruff check .` clean.
Everything local — no commits.

### H1-E · Starter rule library 15 → 33 (§14.5 step 3)

- Added 18 broad OISD/CSB fatal-combination rules (toxic gases H2S/SO2/NH3/Cl2,
  oxygen enrichment, and non-gas permits: isolation/LOTO, work-at-height,
  radiography, excavation, electrical, line-breaking, hot-tapping, lifting,
  vessel entry). Every new rule keys on ≥1 hazard kind absent from the replay
  datasets, so **replay lead-time numbers are byte-identical** (28/25/19/25 min).
- Guard test `test_rule_library.py` enforces: ≥30 valid rules, engine-supported
  predicate types only, and the no-replay-collision invariant.
- Commissioning go-live bar raised to 30 (advisory). Isolation compliance gap now
  closes via the LOTO rules; tank-farm + startup remain honest gaps.

### H1-F · Integration hub / connector SDK (§14 Phase 4)

- New `services/connectors`: `Connector` protocol → canonical events; real
  `csv-historian` (reuses `verge_edge.normalize_opcua` via a tag map) and
  `csv-cmms` adapters; degraded-by-default proprietary stubs (PI Web API,
  Honeywell PHD, SAP PM, Maximo, Milestone VMS); env registry.
- CLI `verge ingest` emits canonical JSONL — pipeable into the risk engine like
  `verge sim`. Proven end-to-end: CMMS + historian → 3 compound findings
  (incl. the new isolation-breach rule).

### H1-G · Hash-chained incident report generator (§14 Phase 3 — audit)

- `services/compliance/incident_report.py`: final, audit-backed, deterministic
  (LLM-free) incident report from a finding + its audit trail + evidence + linked
  OISD clauses; content hash bound to the audit head (reproducible, tamper-evident).
- API `GET /api/findings/{id}/incident-report`; CLI `verge incident-report`.

### H1-H · Model registry + drift (§14 Phase 4 — MLOps)

- New `packages/mlops`: file-backed model registry with a
  registered→shadow→canary→production→retired lifecycle (legal transitions,
  one-production-per-name), and a dependency-free PSI drift detector with severity
  bands. Bundled demo registry.
- API `GET /api/models`; registry rollup in `/api/ops/status` + `/metrics`
  (`verge_models_total`); CLI `verge models`.

### Workspace changes

- Registered `packages/mlops`, `services/connectors` in root `pyproject.toml` +
  `conftest.py`; declared deps in `services/api` and `cli` pyprojects.
- `main.py`: model registry state + `/api/models`, `/api/vision`, connectors CLI.
- README, ARCHITECTURE, and package READMEs updated.

## 2026-07-07 - Early Horizon 1 prep, phases I–J (agent / main track)

Ended at 245 tests green, `ruff check .` clean. Everything local — no commits.

### H1-I · Operator-gated multi-channel alert dispatch (§4.4, P8)

- `services/orchestrator/dispatch.py`: channel adapters (console always delivers;
  sms/ivr/pa/app external → degraded without a provider, honest not fabricated),
  `dispatch_alert` **refuses without an approver** (P8), returns a hash-chainable
  delivery receipt.
- API `POST /api/findings/{id}/alert/dispatch` — drafts, delivers, audit-appends
  the receipt (including a refused unapproved attempt as P8 evidence).

### H1-J · Schema registry + data contracts (§14 Phase 4)

- New `packages/contracts`: versioned `EventContract`s for reading/permit/shift
  with typed field checks (str/number/bool/iso-datetime, choices), a
  `ContractRegistry` (latest-per-type), and `validate_stream`. Dependency-free.
- CLI `verge validate` checks a canonical-event JSONL stream (pairs with
  `verge ingest`); non-zero exit on any violation — a pre-ingest/CI gate.

### Workspace

- Registered `packages/contracts` in root `pyproject.toml` + `conftest.py`;
  declared CLI dep. Orchestrator exports dispatch; API registers the alerts router.

## 2026-07-07 - Early Horizon 1 prep, phases K–L (agent / main track)

Ended at 254 tests green, `ruff check .` clean. Everything local — no commits.

### H1-K · Regulatory-change monitoring (§14 Phase 3)

- `services/compliance/changes.py`: content **fingerprint** of the clause library
  + field-level `diff_clauses` (added/removed/modified) vs. a bundled certified
  prior snapshot (`clauses/oisd-2023.json`). API `GET /api/compliance/changes`.

### H1-L · Capstone Horizon-1 pipeline integration test

- `tests/integration/test_horizon1_pipeline.py`: connector ingest → contract
  validation → risk engine (compound + isolation-breach + SIMOPS findings) →
  hash-chained incident report → compliance assessment. The cross-module
  regression net for everything built this run.

### H1-M · Backup / restore audit-chain verification (§14.6)

- `services/api/verge_api/backup.py`: `snapshot_audit` exports the chain;
  `verify_snapshot` rebuilds + replays it, rejecting any linkage break, head
  mismatch, or content-hash mismatch (P6). Timestamps normalized to canonical
  form so a snapshot verifies regardless of serialization (`Z` vs `+00:00`).
- API `GET /api/ops/backup` + `POST /api/ops/backup/verify`; CLI `verge backup
  create|verify`. Tamper-detection tests (middle + last entry).

### H1-N · Model router (§14 Phase 4)

- `packages/mlops/router.py`: routes a scoring request to the production model,
  or the canary for its configured rollout zones; degraded (→ rules fallback, P1)
  when no model. API `GET /api/models/route`.

### H1-O · Edge autonomy mode (§14 Phase 4; P1/P7)

- `services/edge-gateway/autonomy.py`: `EdgeAutonomy` runs the deterministic
  safety core **locally** when the central link is down (fail-operational, P1)
  and store-and-forwards every event, flushing in order on reconnect (P7). Engine
  injected (dependency inversion) so edge-gateway stays schema-only. Test proves
  a hot-work + rising-gas finding fires offline.

### H1-P · Plant-IT observability config (§14.6)

- `deploy/observability/`: Prometheus scrape config (+ audit-broken / ingest-
  stalled alert rules) and an importable Grafana dashboard (audit integrity,
  ingest, sensor-health pie, degradation posture, model count, uptime) over the
  `/metrics` surface. Completes the §14.6 Prometheus + Grafana plant-IT surface.
- Documented all new env toggles in `.env.example` (vision, connectors, alert
  channels, model registry, backup/bundle timestamps). `make demo-h1` tour +
  `commission`/`compliance`/`models` targets.

## 2026-07-07 - Backend hardening pass (H1-Q, agent)

Adversarial review (parallel reviewers) + fixes across the Horizon-1 modules.
Tests 268 → 282 green, ruff clean. Real issues fixed:

- **Non-finite poison data (safety-critical):** NaN/inf gas readings silently
  defeat threshold rules (`nan >= limit` is always False). Now rejected in the
  data contracts (`number` requires `math.isfinite`), the CSV historian
  connector, and the PSI drift monitor (NaN in the reference previously yielded a
  false "stable").
- **Crashes on reachable inputs:** `ops.livePct` ZeroDivisionError on all-zero
  sensor-health counts; `incident_report._timeline` TypeError when a real audit
  trail mixes datetime + missing timestamps. Both fixed + tested.
- **`since` windowing** compared ISO strings (wrong across tz offsets / naive-vs-
  aware) → now compares parsed instants. **BOM** on CSV exports silently blanked
  every row → read as `utf-8-sig`.
- **Compliance integrity:** duplicate clause ids (would inflate the coverage
  ratio and hide a regulatory change) now a hard error; `changed` flag derived
  from the visible diff (no "changed but nothing to show"); incident-report hash
  aligned to the rendered artifact.
- **Backup verification honesty (§14.6):** a fully re-forged chain passes self-
  referential checks — added an out-of-band `expected_head` anchor and corrected
  the docstring/claim (internal-consistency vs proof-of-authenticity).
- **Robustness:** contracts `latest()` now semver-ordered (1.10 > 1.9);
  `validate_stream` surfaces truncation honestly; ops vision probe degrades
  instead of crashing the health surface; model registry tolerates unknown
  fields (forward-compat) and writes atomically.

Second review round (geometry, commission, vision, dispatch):

- **Safety-critical geometry:** `polygons_overlap` replaced the fragile
  centroid-nudge probe with exact strict vertex-containment — now correct on
  non-convex (L/U-shaped) zones, which drive SIMOPS adjacency.
- **P8 safety-gate bypass:** a whitespace-only approver satisfied the dispatch
  approval gate — now stripped/rejected; a refused attempt is attributed to
  "anonymous", never "system" (P6/P8 attribution).
- **Vision degrades, never raises (P4):** malformed annotation confidence/ts/bbox
  are skipped/repaired instead of crashing the plane; a corrupt annotations file
  degrades to the stub instead of crashing app wiring.
- **Commission:** sensor/layout CSV read as `utf-8-sig` (BOM no longer silently
  drops data); duplicate zoneIds flagged invalid (no data loss / self-overlap);
  a sensor exactly on a shared zone edge is left unassigned (deterministic);
  non-finite coordinates rejected.
- **Dispatch:** duplicate channels de-duplicated (no double-send); removed a
  private-symbol import via a public `phrase_for()` helper.

Third pass — geometry fuzz (safety-critical, drives SIMOPS adjacency):

- Added a seeded 4000-case fuzz test comparing `polygons_overlap`/`polygons_touch`
  against analytic ground truth for random axis-aligned rectangles. It drove out
  two real bugs: (a) `polygons_touch` reported adjacency for polygons that
  *overlap and also share an edge* (now excludes overlap); (b) `polygons_overlap`
  missed collinear-boundary overlaps (axis-aligned zones overlapping along a
  shared edge-line) — fixed with a bounding-box-intersection-midpoint probe plus
  a guaranteed-interior-point containment test. Adjacency/overlap are now
  fuzz-verified correct for the rectilinear layouts plants actually draw.

Tests 268 → 296 (+28 regression + fuzz guards). `ruff check .` clean.

### Horizon 1 prep — run totals

16 phases (H1-A…H1-P) + hardening (H1-Q). New packages: `packages/mlops`, `packages/contracts`. New
services: `services/compliance`, `services/vision`, `services/connectors`. New
CLI verbs: `commission`, `plant`, `sensor`, `rules adopt`, `compliance`,
`incident-report`, `ingest`, `validate`, `models`. New API routes: compliance
(report/gaps/changes/incident-report), vision, models, ops (+/metrics), alert
dispatch. Rule library 15 → 33. Tests 152 → 254, all green; ruff clean.
