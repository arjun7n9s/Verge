# Verge — Design & UX Plan

**Document:** `design_plan.md`  
**Status:** Active planning (2026-07-19)  
**Scope:** Operator console only (`apps/console`) — structure, craft, and usefulness  
**Not this doc:** Backend phases, agents, infra — see [`PHASED_BUILD_PLAN.md`](./PHASED_BUILD_PLAN.md)  
**Tokens & components:** [`design-system.md`](./design-system.md) (Instrument Paper)

---

## 1. Purpose

Define how Verge *looks and feels* to an operator: elegant, calm, visually meaningful, and useful — without merging Live Risk, chat, graph, and admin into one overloaded dashboard.

This plan is the **source of truth for UI/UX**. Engineering phases implement against it; they do not redefine the product surfaces.

---

## 2. Design principles

| # | Principle | Meaning |
|---|---|---|
| D1 | **One job per page** | Each route has one headline and one primary action path. |
| D2 | **Elegant restraint** | Instrument Paper: cold canvas, hairline rules, IBM Plex. No dark-cyber clichés, no decorative gradients, no glassmorphism. |
| D3 | **Signal is sacred** | Orange / red / blue bands mean lead-time or danger — never decoration, title hover, or “AI glow.” |
| D4 | **Useful over impressive** | Every control hits a real API or is honestly disabled. Empty is allowed; fiction is not. |
| D5 | **Short paths** | Triage → finding → act; or Copilot → ask / upload. No training required for the happy path. |
| D6 | **Separate wedges** | Live Risk and Living Knowledge are peers in the nav — not nested panels of each other. |

---

## 3. Visual system (summary)

Full tokens live in [`design-system.md`](./design-system.md). Non-negotiables for this plan:

- **Canvas** `#F0F1EF` · **panels** white · **ink** `#121417` · **dim** `#5C6068`
- **Type:** IBM Plex Sans (UI) · IBM Plex Mono (IDs, readings, timestamps only)
- **Hierarchy:** page `h1` 18px sentence-case · finding titles 14px/600 · micro-labels 10px mono uppercase only
- **Elevation:** borders, not shadows (floating layer only for modal / ⌘K / toast)
- **Motion:** IMMINENT pulse, map fly-to, citation highlight — then stop; respect `prefers-reduced-motion`

---

## 4. Anti-patterns (do not ship)

| Anti-pattern | Why |
|---|---|
| Mega-dashboard (map + board + chat + graph + admin on `/`) | Cognitively noisy; nothing is primary |
| Fake KPIs / hardcoded muster / invented citations | Breaks P4 and operator trust |
| Unlabeled seed data as “live plant” | Demo must be labeled or off |
| Fake photo attach / fake radio ticker | Disabled + reason until real ids exist |
| Purple/glow “AI” chrome on Copilot | Conflicts with Instrument Paper |
| Equal-weight side panels on home | Use dedicated routes or finding page |

---

## 5. Information architecture

```text
Shared chrome: Logo · Nav · ⌘K · Language · Stream · LIVE/SHADOW · Degrade strip
             (+ Sensor ribbon only on Board / Map — not on Copilot / Audit)

Live Risk                          Living Knowledge
─────────                          ────────────────
/            Board (triage)        /knowledge   Plant Copilot (chat + ingest)
/map         Map focus (optional)  /graph       Relationship explorer
/findings/:id  One finding depth

Support
───────
/handover    Shift continuity
/replay      Rehearse / prove
/audit       Integrity & evidence
/fleet       Multi-site (honest nulls)
/admin       Plant IT (sectioned)
```

### Route jobs

| Route | One job | Primary UI | Keep out |
|---|---|---|---|
| `/` | Triage live findings | Lead-time board, filters → open finding | Chat, full graph, admin dumps, permanent emergency wall |
| `/map` | Spatial situation | Twin map; select zone → filter or open finding | Corpus, free chat |
| `/findings/:id` | Understand & act on **one** finding | Summary · Live · Investigate · Ask (link) · Respond | Plant-wide chat history, full graph canvas |
| `/knowledge` | Ask plant docs; grow corpus | Threaded cited chat + ingest rail | Risk columns, IMMINENT theater |
| `/graph` | Explore relationships | Live twin / Neo4j drill-in | Triage board, Copilot thread |
| `/handover` | Shift handoff | Notes + Melia transcript when available | Full corpus admin |
| `/replay` | Prove a story | Replay / eval linkage | Live ops clutter |
| `/audit` | Integrity | Hash chain, packs | Findings triage |
| `/fleet` | Multi-site glance | Honest nulls where unmeasured | Fake bulletins |
| `/admin` | Configure plant IT | Sectioned ops / models / thresholds | Operator home |

---

## 6. Surface designs

### 6.1 Board — Live Risk triage

**Mood:** Ops room first, triage second — industrial situation awareness without a mega-dashboard.

- **Live Ops stage (mandatory):** multi-cam wall (MJPEG/snapshot from registry `source` / `VERGE_VISION_RTSP_URL`) + radio transcript rail with optional clip playback on `/`. Honest empty labels when quiet — never hide the whole stage. Detection stills from `detect-frame` (`/api/vision/frames/{id}`); demo sources are labeled DEMO, never invented plant CCTV.
- **Continuous Watch (product heartbeat):** officer toggles **Watch on** → API `POST /api/watch/start` runs vision sample + radio chunks + sensor schedule → live fusion → findings SSE + Cognee. No frontend-hardcoded findings.
- **Triage:** band-first finding list by default (IMMINENT → NEAR → WATCH); column kanban available as a toggle.
- Optional Map / Response side rails — closed by default; never permanent equal panels.
- Click finding → **`/findings/:id`** (full page). Prefer page over kitchen-sink modal.
- Chrome: sensor ribbon + degrade strip. Chips alone are **not** sufficient for summit Live presence.

**Empty:** calm empty state when no findings (`VERGE_SEED=off` and no live data); Live Ops stage still shows labeled empty feeds.

### 6.2 Finding page — depth

Sequential, readable sections (tabs or ruled blocks):

1. **Summary** — band, zone, title, counterfactual  
2. **Live** — zone live cam (or last still), radio + audio clips, synced incident timeline (vision/radio/sensors), telemetry window, active permits  
3. **Signals** — lineage chips + convergence chart  
4. **Investigate** — orchestrator brief, specialists, validator disposition  
5. **Ask** — deep-link to Copilot scoped to this finding (`/knowledge?finding=…`)  
6. **Respond** — ack, escalate, resolve, evidence export (rail)  

Links out to `/graph` when the operator needs plant topology — do not embed a full explorer here.

### 6.3 Plant Copilot — AI chat + ingest

**Mood:** Quiet, document-forward, generous whitespace. This is the Living Knowledge product.

**Jobs**
1. Ask — grounded, multi-turn chat  
2. Ingest — SOPs / PDFs / markdown; field photos when API returns a real asset id  
3. Browse corpus — status, open citation sources  

**Layout**
```text
┌── Corpus (support) ───┬──── Chat (focus) ────────────────────┐
│ Upload · list · type  │ Thread                               │
│ chips: doc | photo    │   answer + citation rail per turn    │
│                       │ Composer (+ attach)                  │
└───────────────────────┴──────────────────────────────────────┘
```

**Contracts**
- Answer only from DocIntel / Cognee (and finding-scoped tools when linked).  
- Every turn: citations or honest “cannot answer from corpus.”  
- Not free-form ChatGPT about the plant.  
- Not the P1 risk engine.

### 6.4 Graph — exploration room

Own route. Live data only. Filter, click → object or finding. Never hardcoded nodes.

### 6.5 Mobile

Separate short flows — not a shrunk mega-dashboard:

- List → finding → ack  
- Copilot ask  
- Photo evidence (disabled until store id)  
- Muster check-in  

One-thumb reach for primary actions.

### 6.6 Wallboard (optional)

Dim, IMMINENT-first, 10m readability. Same live APIs. No decorative metrics.

---

## 7. Shared chrome

| Element | Behavior |
|---|---|
| Header (48px) | Logo, editorial nav underline, search ⌘K, language, stream, LIVE/SHADOW |
| Degrade strip | One collapsed line (`DEGRADED · N`); expand for list — never stacked tinted bars |
| Sensor ribbon | Board/Map only; single truncating line |
| ⌘K | Jump to routes / findings — not a second Copilot |

---

## 8. Content & trust

| Topic | Rule |
|---|---|
| Seed / demo | Labeled in chrome when `VERGE_SEED=demo`; never silent |
| Unmeasured | Null or omit — never invent TRIR / fatigue / % compliant |
| Copilot | Cited or degraded — never invent SOP text |
| Photos / voice | Success only with stored asset / event id |

---

## 9. Implementation order (UI track)

Independent of backend phase numbers; coordinate APIs as needed.

| Step | Work | Outcome |
|---|---|---|
| U1 | **Route clarity** — Board triage-first; Finding full page; Copilot chat focus; Graph own route | IA matches this plan |
| U2 | **Declutter `/`** — remove panel sprawl (chat/graph/admin-like blocks) | Home is elegant triage |
| U3 | **Plant Copilot v1** — threaded chat + ingest well (docs; photos when API ready) | Living Knowledge usable |
| U4 | **Finding page** — replace modal-only depth | &lt;30s understanding path |
| U5 | **Fiction audit** — seed labels, null KPIs, disabled fakes | P4 on every surface |
| U6 | **Polish** — motion budget, mobile one-thumb, pack switcher chrome when packs exist | Summit-ready craft |

---

## 10. Success criteria

- Operator triages a NEAR finding Board → Finding in **&lt;30s** without opening Copilot or Graph.  
- Operator gets a **cited** Copilot answer (or honest empty) in **&lt;15s** without seeing the risk board.  
- Home does not require scrolling through chat, graph, and admin to see findings.  
- Blind tester describes the product as “calm / clear,” not “busy dashboard.”  
- `VERGE_SEED=off` + no ingest → empty Board and empty corpus.

---

## 11. Document map

| Doc | Role |
|---|---|
| **`design_plan.md`** (this file) | UI/UX structure & craft intent |
| [`design-system.md`](./design-system.md) | Tokens, type, hard visual rules |
| [`PHASED_BUILD_PLAN.md`](./PHASED_BUILD_PLAN.md) | Engineering phases; §0 points here for UI |
| [`GENAI_ARCHITECTURE_AUDIT.md`](./GENAI_ARCHITECTURE_AUDIT.md) | Advisory GenAI constraints (P1 fence) |
| [`progress.md`](./progress.md) | Session log |

---

## 12. Changelog

| Date | Note |
|---|---|
| 2026-07-19 | Initial `design_plan.md`: one job per page; Plant Copilot; no mega-dashboard; no fiction |
| 2026-07-20 | Added §13 Premium craft escalation (backed by [`design-resources/`](./design-resources/README.md)); Ash IA handoff (finding page, graph, Copilot thread) — U2–U6 partial, not complete |
| 2026-07-20 | §6.1 Live Ops stage mandatory; band-first triage default; finding **Live** section; vision frame HTTP cache |
| 2026-07-20 | §6.1 multi-cam MJPEG wall + radio audio clips; §6.2 incident timeline scrubber; `/api/cameras`, `/api/voice/clips` |
| 2026-07-21 | Continuous WatchLoop (`/api/watch/*`) — vision/radio/sensors → fusion → Cognee; Live Ops Watch on/off |

---

## 13. Premium craft escalation

**Premise:** "Premium" is earned through craft depth, not chrome. The visual
references and explicit adopt/reject verdicts live in
[`design-resources/README.md`](./design-resources/README.md) — Anduril's
Lattice page is the north star; neon-gradient "AI dashboard" chrome is the
labeled anti-pattern. Nothing in this section relaxes the hard rules of
[`design-system.md`](./design-system.md); it spends *within* them.

### 13.1 Typographic confidence

The system's scale tops out at `xl` (22px) for ordinary surfaces. Each route
may additionally spend **one display moment** — a single element at 28–36px
that carries the page's meaning:

| Route | The one display moment |
|---|---|
| `/findings/:id` | The lead-time band as a standing **mission clock** (band word in band color, window line beneath) — not a KPI tile |
| `/` (empty) | Calm editorial empty state — confidence shown by whitespace, not a spinner |
| `/knowledge` (empty thread) | The ask prompt as an invitation, not a toolbar |

Rules: sentence case (never uppercase display type), IBM Plex Sans 600,
`tabular-nums` when numeric, and band color **only** when the element *is*
the band. Two display moments on one screen means neither is one.

### 13.2 Motion system

A named budget, not ad hoc transitions. Everything uses the existing 150ms
ease token; anything not in this table does not move.

| Name | Trigger | Motion | Budget |
|---|---|---|---|
| Annunciator pulse | IMMINENT band only | opacity pulse ~1.2s | reserved — never reused |
| Press | button active | `scale(0.98)` | all buttons |
| Elevate | card/row hover | border `--line` → `--line-2` | color only — no shadow, no scale |
| Fly-to | map zone select | camera ease | map only |
| Citation flash | citation click → source | one background flash, then stop | knowledge surfaces |
| Page settle | route enter | 150ms fade/2px rise, once | never on data refresh |

`prefers-reduced-motion` kills every row, including the pulse (state stays
visible through color and the band word).

### 13.3 Data-viz, edited

Plotting is not designing. Every chart must pass: (1) it states one finding a
sentence could not; (2) direct labels over legends when ≤3 series; (3) grid
recessive (`#ECEAE4`), axes earn their place; (4) band/status colors appear
only as threshold reference lines — series use the categorical palette;
(5) no sparkline confetti — a number with a stable denominator beats a
2-point trend; unmeasured stays null (§8), never interpolated.

### 13.4 Tactile hero instruments

Budget: **at most two components in the whole console** may carry material
rendering (the metallic-widget reference, adopted narrowly):

1. `LeadTimeGauge` on `/findings/:id` — the one instrument that reads as a
   physical gauge (subtle inner bevel / specular edge is allowed).
2. A future IMMINENT alert orb, if one ships.

Constraints: CSS-only (no textures/images), works on paper white, respects
reduced motion, and never appears in lists or cards at large. If every panel
goes glossy, none of it means anything (D3 — signal is sacred).
