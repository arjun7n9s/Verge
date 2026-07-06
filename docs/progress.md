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
