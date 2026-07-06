# Dex — parallel workstream (shared local workspace)

> **Purpose:** Ship a large chunk of Verge in parallel — **same repo folder on disk**, no separate GitHub accounts. Arjun’s team commits and pushes; you work locally in your lane.  
> **Read first:** [`README.md`](../README.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`Verge.md`](Verge.md)  
> **You own:** backend intelligence layer (new code + new API routes).  
> **You do not touch:** `apps/console/**` (Anshuman / console track).

---

## How we work in one folder without stepping on each other

No branches required on your side. **Stay in your directories** and use the lock file so nobody edits the same file at once.

### 1. Directory ownership (most important)

| Path | Who | Dex may edit? |
|---|---|---|
| `packages/memory/**` | **Dex** | **Yes** (create + own) |
| `services/voice/**` | **Dex** | **Yes** (create + own) |
| `services/api/verge_api/routes/**` | **Dex** | **Yes** (new route files only) |
| `services/api/tests/test_memory*.py`, `test_voice*.py` | **Dex** | **Yes** |
| `apps/console/**` | Anshuman | **No** |
| `services/risk-engine/**` | Main / agent | **No** |
| `eval/**` | Main / agent | **No** |
| `services/twin/**` | Main / agent | **No** |
| `services/api/verge_api/store*.py` | Main / agent | **No** — ask if you need a store method |
| `deploy/**`, `.env.example` | Arjun | **No** |
| `packages/schema/**` | Shared | **Ask first** — schema changes affect everyone |
| `services/api/verge_api/main.py` | Shared | **Ask first** — only add `include_router(...)` lines |
| Root `pyproject.toml` | Shared | **Ask first** — one line to register your package |

### 2. Lock file — `docs/WORK.lock`

Before editing anything **outside your owned folders**, or any **shared** file:

1. Open `docs/WORK.lock` (create if missing).
2. Add a line: `Dex | packages/memory | D1 scaffold | ~2h | 2026-07-06 22:00`
3. When done, **delete your line** or mark `DONE`.

If someone else’s line is on a path you need, **wait or message them** — don’t edit that path.

Example `docs/WORK.lock`:

```
# path | owner | task | until
apps/console | Anshuman | api-wire | evening
eval/harness.py | agent | runtime-parity | done
services/api/verge_api/main.py | Dex | add memory router | 30min
```

### 3. Shared-file rules

**`main.py`** — only append, never refactor:

```python
from .routes.memory import router as memory_router
app.include_router(memory_router, prefix="/api")
```

**Root `pyproject.toml`** — only add your workspace member under `[tool.uv.workspace]` / members list. One small edit, then run `uv sync`.

**Never edit** while someone else has it in `WORK.lock`.

### 4. Git / GitHub (Arjun’s team only)

- You **do not** push to GitHub.
- Work on `main` locally (or stay uncommitted until sync — team preference).
- Before you stop for the day: run tests below and tell Arjun **what files you changed** (list paths).
- Arjun / agent reviews and commits with message like `feat(memory): Dex — Cognee client scaffold`.

### 5. Local env

Use the shared `.env` in repo root (Arjun already filled keys). You need:

- `COGNEE_API_KEY` + set `VERGE_COGNEE_ENABLED=true` when testing memory
- `SPEECHMATICS_API_KEY` when testing voice
- `AIMLAPI_API_KEY` only for D4/D6 summary text (optional)

**No space after `=`** in env values. Don’t commit `.env`.

### 6. Verify before you hand off

```bash
uv sync
uv run pytest                    # whole suite must stay green
uv run ruff check .
uv run pytest packages/memory services/voice services/api/tests/test_memory.py services/api/tests/test_voice.py -q
```

If pytest fails on **their** code, note it — don’t fix files outside your lane unless asked.

---

## Your mission (2-week sprint)

Build the **intelligence layer backend** the console will call later:

1. **Cognee memory** — incident / regulatory / plant context for a finding  
2. **Speechmatics voice** — handover / near-miss transcription → structured evidence  
3. **API routes** — real HTTP endpoints (no mock responses in production paths)

Safety core (`risk-engine`) stays **LLM-free**. Your code must **degrade** (empty + `degraded: true`), not 500, when cloud keys are missing or APIs fail.

---

## Sprint tasks (Dex)

Check boxes here when done; Arjun commits after review.

### Week 1 — Foundation

#### D1 · Scaffold `packages/memory` (Cognee Cloud)

- [x] Create `packages/memory/` + `pyproject.toml` (ping before editing root `pyproject.toml`).
- [x] `verge_memory/client.py` — Cognee Cloud HTTP client (`COGNEE_*`, `VERGE_SITE_ID` env).
- [x] `verge_memory/datasets.py` — dataset name `{COGNEE_DATASET_PREFIX}-{VERGE_SITE_ID}`.
- [x] `verge_memory/ingest.py` — `ingest_closed_finding(...)`, `ingest_document(...)`.
- [x] `verge_memory/retrieve.py` — `context_for_finding(finding)` → similar incidents, clauses, plant history, `degraded`.
- [x] Unit tests with mocked HTTP — **no real network in CI**.

---

#### D2 · Seed corpus (static)

- [x] `packages/memory/verge_memory/corpus/vizag-2025-summary.md`
- [x] `packages/memory/verge_memory/corpus/oisd-stubs.json` (5–10 clauses)
- [x] Idempotent ingest on first retrieve
- [x] `packages/memory/README.md`

---

#### D3 · API route — memory

- [x] `services/api/verge_api/routes/memory.py`
- [x] `GET /api/findings/{finding_id}/context`
- [x] Register router in `main.py` (lock file first)
- [x] `services/api/tests/test_memory_routes.py`

Stable response shape:

```json
{
  "findingId": "F-CONV-07",
  "similarIncidents": [{ "title": "...", "year": 2025, "excerpt": "...", "source": "..." }],
  "regulatoryClauses": [{ "id": "OISD-137-4.2", "title": "...", "excerpt": "..." }],
  "plantHistory": [{ "findingId": "...", "summary": "...", "closedAt": "..." }],
  "degraded": false
}
```

---

#### D4 · Scaffold `services/voice` (Speechmatics)

- [x] `services/voice/verge_voice/transcribe.py`
- [x] Env: `SPEECHMATICS_*`
- [x] Return transcript + `structured` + `degraded`; optional one-line aimlapi summary only
- [x] Mocked tests

---

### Week 2 — Integration

#### D5 · API routes — voice

- [x] `services/api/verge_api/routes/voice.py`
- [x] `POST /api/voice/transcribe`
- [x] `POST /api/voice/handover` (+ audit append via store — ask if you need a helper)
- [x] `services/api/tests/test_voice_routes.py`

---

#### D6 · Shift handover report (optional)

- [x] `POST /api/reports/shift-handover` — facts + aimlapi narrative, template fallback, never auto-submit

---

#### D7 · MinIO manifest stub (optional)

- [x] Upload JSON manifest when `MINIO_*` configured; skip silently otherwise

---

#### D8 · Handoff notes

- [x] READMEs + curl examples in package READMEs
- [x] Update **Dex demo** section below when D3+D5 work

---

## Phase 2 — Intelligence depth (Dex, parallel heavy lifting)

> **D1–D9 done.** **Sprint B done and committed** (2026-07-07). D16 optional remains open.

### Sprint B — Intelligence Platform — complete

**Goal:** Production-grade intelligence layer — not demo polish. Same degradation rules as Phase 1.  
**Estimate:** 1–2 full days. Do not pick individual D10–D16 tasks à la carte; deliver Sprint B as one handoff.

| Step | Task | Deliverables |
|---|---|---|
| B1 | **D13** Cognee hardening | Retry/backoff + timeouts in `client.py`; `dataset_health()`; `GET /api/memory/status` |
| B2 | **Corpus expansion** | `jaipur-2009-summary.md`, `bp-texas-2005-summary.md`, expand `oisd-stubs.json` to 15+ clauses; idempotent ingest |
| B3 | **D12** Evidence retrieval | `routes/evidence.py` → `GET /api/evidence/{pack_id}` from MinIO; degrade when down |
| B4 | **D11** Near-miss voice | `near_miss.py` + `POST /api/voice/near-miss` + audit append + tests |
| B5 | **D14** Alert preview | `POST /api/findings/{id}/alert/preview` → `{ languages: { en, hi }, degraded }`; template fallback |
| B6 | **D15** Integration tests | `tests/integration/test_memory_voice_path.py` — full HTTP path, mocked Cognee + Speechmatics |
| B7 | **D10** Feedback loop | `ingest_feedback()` in memory; coordinate with main track — hook lives in `hooks.py` (ask before wiring) |

**Sprint B paths (claim all in WORK.lock):**

```
packages/memory/**
services/voice/**
services/api/verge_api/routes/memory.py
services/api/verge_api/routes/voice.py
services/api/verge_api/routes/evidence.py   (new)
services/api/tests/test_memory*.py
services/api/tests/test_voice*.py
tests/integration/test_memory_voice_path.py (new)
```

**Do not start Sprint B until you read `docs/WORK.lock` — main track may be on `hooks.py` or `main.py`.**

---

- [x] `POST /api/memory/query` — body `{ "query": "...", "findingId": "..." }`
- [x] Uses Cognee search; returns `{ "answer", "citations", "degraded" }`
- [x] `services/api/verge_api/routes/memory.py` + `packages/memory/verge_memory/query.py`
- [x] Tests with mocked HTTP only

#### D10 · Feedback → memory loop

- [x] On `POST /api/findings/{id}/feedback`, optionally ingest operator rationale to Cognee
- [x] `ingest_feedback(finding_id, verdict, reason_code)` in `packages/memory`
- [x] Hook via API (ask before editing `main.py` transition/feedback handlers — or add hook in `hooks.py` owned by main track)

#### D11 · Voice near-miss endpoint

- [x] `POST /api/voice/near-miss` — transcript + structured hazards/zones/actions
- [x] Optional `findingId` link; always audit-append
- [x] `services/voice/verge_voice/near_miss.py` + route + tests

#### D12 · Evidence retrieval

- [x] `GET /api/evidence/{pack_id}` — fetch manifest JSON from MinIO when configured
- [x] Degrade to `{ "degraded": true, "reason": "..." }` when MinIO down
- [x] Own `services/api/verge_api/routes/evidence.py` (Dex) — do not refactor `evidence_store.py` without lock

#### D13 · Cognee production hardening

- [x] Retry/backoff + timeout tuning in `packages/memory/verge_memory/client.py`
- [x] `dataset_health()` probe; expose in `GET /api/memory/status`
- [x] Corpus expand: 2–3 more incident summaries (Jaipur, Texas City stubs)

#### D14 · Multilingual alert narratives

- [x] `packages/narrative/` or extend `services/voice` — aimlapi draft for orchestrator alert bodies
- [x] `POST /api/findings/{id}/alert/preview` — returns `{ "languages": { "en": "...", "hi": "..." }, "degraded" }`
- [x] Template fallback when LLM down (mirror `shift_handover.py` pattern)

#### D15 · Intelligence integration tests

- [x] `tests/integration/test_memory_voice_path.py` — mocked Cognee + Speechmatics, full HTTP path
- [x] Document curl matrix in `packages/memory/README.md`

#### D16 · Transcript persistence (optional)

- [x] `GET /api/voice/handover/recent?limit=20` — audit-backed (SQL durable when `VERGE_STORE=sql`)

**Dex Phase 2 paths:** `packages/memory/**`, `services/voice/**`, new files under `routes/`, `test_memory*.py`, `test_voice*.py`, optional new package with root `pyproject` ping.

---

## Definition of done (each chunk of work)

- [ ] Only touched **your** paths (+ shared files with lock + OK from Arjun)
- [ ] `uv run pytest` green
- [ ] `uv run ruff check .` clean
- [ ] No secrets in code
- [ ] Cloud down → `degraded: true`, not fake data
- [ ] Message Arjun: list of changed files + which task (D1–D8)

---

## What NOT to do

- Don’t edit `apps/console/**`
- Don’t edit `risk-engine`, `eval`, `forecaster`, `twin`
- Don’t return fabricated findings or fake API success when offline
- Don’t `git push` (team handles GitHub)
- Don’t edit a file that’s in someone else’s `WORK.lock` line

---

## Sync rhythm (shared desk)

| When | What |
|---|---|
| **Start of session** | Read `WORK.lock`; claim your paths |
| **Before shared file** | Add lock line + quick message |
| **End of session** | Run pytest; clear lock; send file list to Arjun |
| **2×/week** | 10 min: who’s on what task next |

---

# Main team track (Arjun + Anshuman + agent)

> Same workspace. **Don’t edit `packages/memory/**` or `services/voice/**`** while Dex is on D1–D5.

| Track | Paths | Who |
|---|---|---|
| Console | `apps/console/**` | Anshuman |
| Safety core + eval | `services/risk-engine/**`, `eval/**` | Agent / Arjun |
| Twin + geo API | `services/twin/**`, `routes/plant.py` | Agent |
| Git / deploy / env | `.env.example`, `deploy/**`, commits | Arjun |

### M1 · Console stabilize

- [x] API contract, mock removal, KnowledgePanel, audit, map, handover, permits panel
- [x] FleetView wired to `/api/fleet/summary`
- [ ] Mobile field worker panel (sensor ribbon + voice API)

### M2 · Eval — [x] runtime parity, band calibration, vizag plantModel

### M3 · Rules — [x] 16 rules

### M4 · Live path — [x] demo-live, findings + permit POST sync

### M5 · GeoJSON — [x] done

### M6 · API surface — [x] permits, reports, memory, voice

### M8 · Console zero-mock checkpoint (agent)

- [x] FleetView → `/api/fleet/summary`
- [x] PermitsPanel → live API
- [x] KnowledgePanel → context + free-text query
- [x] MobileFieldWorkerPanel → sensor ribbon + voice handover + live findings
- [x] TemporalConvergenceChart → `/api/findings/{id}/telemetry`
- [x] E2E live path test update (`tests/test_e2e_live_path.py`)

### M9 · Durable pilot stack (agent)

- [x] SqlStore persists permits + sensor readings (same engine as findings)
- [x] Edge gateway `--post-api` forwards readings/permits to API
- [x] `make dev-sql` + deploy docs
- [x] Timescale optional writer on reading ingest (`TIMESCALE_DSN`)

### M10 · Console Sprint B wiring (agent)

- [x] Alert preview in ResponseOrchestrator
- [x] Evidence export via `/api/evidence/{pack_id}`
- [x] Memory status panel in Admin

### M7 · Infra (Arjun) — deploy env, make up

- [x] API + console in compose (`make up-app`, profile `app`)
- [x] `deploy/Dockerfile.api`, multi-stage console image
- [x] Keycloak realm import (`deploy/keycloak/verge-realm.json`)
- [x] Optional OIDC (`VERGE_AUTH_ENABLED`, console Keycloak provider)
- [x] `GET /api/voice/handover/recent` (D16 — audit-backed)

---

## Agent queue (implementation priority)

1. ~~M10 console Sprint B wiring~~ — done
2. ~~M7 deploy hardening~~ — done
3. Keycloak auth in production pilot (enable `VERGE_AUTH_ENABLED` when ready)

**Do not** take Dex Sprint B lanes — check `WORK.lock`.

---

## Integration checklist (test together later)

| Step | Status |
|---|---|
| Sim → API findings + permits | wired |
| Console on real API | done (M8) |
| Telemetry charts | done |
| Memory / voice / audit / map | done |
| Replay harness | done |

---

## API curl reference

```bash
# Memory context (API must be running: make dev or uvicorn)
curl http://localhost:8000/api/findings/F-CONV-07/context

# Voice transcribe
curl -F "file=@handover.wav" http://localhost:8000/api/voice/transcribe

# Voice handover → audit entry
curl -F "file=@handover.wav" -F "actor=maya" http://localhost:8000/api/voice/handover
```

---

## Quick start (day 1)

```bash
cd Verge
uv sync
uv run pytest -q          # baseline green
# Claim in docs/WORK.lock:
# Dex | packages/memory | D1 | ...
# Start D1 scaffold under packages/memory/
```

Questions → Arjun. Spec wins → `docs/Verge.md`.

---

*Last updated: 2026-07-07 — Phase 2 Dex lanes + main-track implementation focus.*
