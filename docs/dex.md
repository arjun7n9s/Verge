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

### M1 · Console stabilize (Anshuman)

- [ ] Merge / integrate console UI locally
- [ ] Fix API contract (`to` not `toState`, `reasonCode` on snooze)
- [ ] Remove silent mock fallback in prod paths
- [ ] Wire `KnowledgePanel` to Dex’s `/context` when D3 lands

### M2 · Eval = live runtime (agent)

- [ ] Shared event accumulator; harness uses SIMOPS + plant YAML
- [ ] Band calibration metric in replay report

### M3 · Rules expansion (agent)

- [ ] `starter.yaml` 4 → 15+ rules + tests

### M4 · Live demo path (agent)

- [ ] Script: sim → risk-engine → API → console

### M5 · Plant GeoJSON (agent)

- [ ] `GET /api/plant/geojson` from twin YAML

### M6 · Git & infra (Arjun)

- [ ] Commit Dex’s work in small chunks after review
- [ ] Fix env spacing; `deploy/.env` passwords; `make up`

---

## Agent queue (Cursor — when Arjun asks)

1. M2 eval parity  
2. M3 rules  
3. M5 GeoJSON  
4. M4 demo script  
5. Help wire console to `/context` after Dex D3  

**Do not** implement `packages/memory` or `services/voice` — Dex owns those.

---

## End-of-sprint demo (together)

| Step | Owner |
|---|---|
| Sim → API → console shows real Vizag finding | M4 + console |
| Finding detail → real `/context` (no fake RAG) | Dex D3 + M1 |
| Voice handover → audit entry | Dex D5 |
| Replay harness with full runtime | M2 |
| Map from `/api/plant/geojson` | M5 + console |

---

## Dex demo (curl) — fill in when D3+D5 land

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

*Last updated: 2026-07-06 — shared workspace model (no Dex GitHub pushes).*
