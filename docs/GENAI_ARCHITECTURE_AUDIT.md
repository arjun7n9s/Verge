# Verge — GenAI / Agentic Architecture Audit (2026)

**Date:** 2026-07-18  
**Purpose:** Research modern industrial GenAI practice, score Verge honestly, and redirect the build plan so we use **aimlapi + Cognee + Speechmatics + Neo4j** at modern depth — without violating P1/P4/P8.

**Companion updates:** [`PHASED_BUILD_PLAN.md`](./PHASED_BUILD_PLAN.md) §7.5 Phase 2.5 GenAI Core + §8 specialists, [`PRODUCT_AUDIT_AND_ROADMAP.md`](./PRODUCT_AUDIT_AND_ROADMAP.md) agents / phase table.

---

## 1. What “modern” looks like in 2026 (research summary)

Sources (indicative): industrial LLM+control safety papers (P&ID-grounded validation, Graph RAG + deterministic validators), Anthropic multi-agent research / context engineering, OpenAI agent-native APIs, production orchestration practice (specialists + orchestrator + evals + OTel).

### Consensus patterns that matter for Verge

| Pattern | Meaning for industry | Keep / adopt |
|---|---|---|
| **Hard split: detect vs advise** | LLMs must not sit in the interlock / trip path | **Already Verge P1 — keep forever** |
| **Deterministic validator around LLM proposals** | Topology, interlocks, permit matrix, forbidden actions checked before any “recommendation” is trusted | **Adopt harder** (today: soft citations only) |
| **Graph RAG / ontology retrieval** | Multi-hop: equipment → zone → permit → clause → SOP — not bag-of-chunks | **Upgrade Cognee+Neo4j to first-class** |
| **Specialist agents + thin orchestrator** | Lead agent plans; sub-agents search telemetry / docs / clauses with clean context; return distilled briefs | **Upgrade from single Investigator** |
| **Just-in-time context** | Tools load evidence on demand; don’t stuff entire plant into the prompt | **Already our tool-loop style — deepen** |
| **Multimodal as one ops moment** | Radio + frame + SOP + telemetry in one investigation | **Wire Melia + vision + docintel into one agent kit** |
| **Structured outputs + evals** | JSON schemas, gold briefs, groundedness / citation metrics | **Expand `eval/` for agents** |
| **Observability** | Trace every tool call, token, degrade reason | **Add agent traces to audit/OTel** |
| **Human-in-the-loop** | Confidence / validation fail → escalate to operator | **Already P8 — make UI explicit** |
| **No PLC write from agents** | Advisory only | **Keep P8** |

### What we should *not* copy blindly

- Autonomous “operator agents” that emit control moves without a deterministic gate (papers show this only with heavy validators — we stay **advisory** for summit).  
- LangChain / proprietary agent clouds as the runtime (conflicts with P2 sovereignty / air-gap story). Keep our **owned tool loop**; optionally speak MCP-shaped tool schemas later.  
- Replacing the risk-engine with an LLM classifier.

---

## 2. Honest scorecard — Verge GenAI today

| Capability | Score (0–5) | Reality |
|---|---|---|
| Safety core LLM-free | **5** | Strong P1; correct for industry |
| Single Investigator tool-loop | **3** | Real, read-only, degrades to fact sheet — but one generalist |
| Knowledge RAG | **2** | Local chunks + aimlapi; Cognee often disabled; weak GraphRAG |
| Multimodal fusion in agents | **1** | Melia + vision + docs exist as APIs; investigator tools don’t fully fuse them |
| Multi-agent orchestration | **1** | Not built — Phase 3 named agents are mostly missing services |
| Validator / “can’t recommend X” gate | **1** | No topology/interlock checker on agent output |
| Agent evals | **1** | Knowledge F1 starter only; no investigator gold briefs |
| Trace / audit of agent steps | **2** | Steps returned in API; not first-class ops telemetry |
| Speech → English ops | **4** | Melia + aimlapi translate path (2026-07-18) |
| Vision in GenAI loop | **2** | Detections as signals; little VLM reasoning in investigator |

**Verdict:** The **skeleton is right** (P1 + tool loop + degrade). The **muscle is thin**. We are under-using GenAI on the *advisory* side while correctly refusing it on the *safety* side. Gap is not “add ChatGPT to the risk engine” — it is **modern advisory depth**.

---

## 3. Target GenAI architecture (deployed plant)

```text
                    ┌─────────────────────────────────────┐
                    │  LIVE RISK (LLM-FREE)               │
  MQTT/permits/     │  risk-engine · SIMOPS · forecaster  │
  voice-event/      │  → RiskFinding + lineage            │
  vision-event ───► │                                     │
                    └──────────────┬──────────────────────┘
                                   │ finding
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  ADVISORY ORCHESTRATOR (aimlapi)    │
                    │  plans · fans out · merges · cites  │
                    └─┬─────────┬──────────┬─────────────┘
                      │         │          │
           ┌──────────▼─┐ ┌─────▼────┐ ┌───▼──────────┐
           │ Telemetry  │ │ Knowledge│ │ Compliance   │
           │ Specialist │ │ Specialist│ │ Specialist  │
           │ (Timescale │ │ (Cognee + │ │ (clauses +  │
           │  permits)  │ │  Neo4j +  │ │  evidence)  │
           │            │ │  docs)    │ │             │
           └──────────┬─┘ └─────┬────┘ └───┬──────────┘
                      │         │          │
                      └─────────┼──────────┘
                                ▼
                    ┌─────────────────────────────────────┐
                    │  VALIDATOR (deterministic)          │
                    │  twin topology · SIMOPS matrix ·    │
                    │  “no invent tags” · citation check  │
                    └──────────────┬──────────────────────┘
                                   │ approved brief
                                   ▼
                              Operator console
                         (human is the interlock)
```

**Still one product, two planes.** GenAI never opens a trip; it explains and proposes with receipts.

---

## 4. Agent roster (target)

| # | Agent | Job | Tools (examples) | Status |
|---|---|---|---|---|
| 0 | **Advisory Orchestrator** | On finding (or operator ask): decompose, call specialists, merge JSON brief | `spawn_*`, merge, validate | **Build** (evolve today’s investigator) |
| 1 | **Telemetry Specialist** | What is the live physics / permit state? | readings window, permits, changeover, sensor health | **Partial** (investigator tools) |
| 2 | **Knowledge Specialist** | What do SOPs / manuals / prior incidents say? | Cognee query, doc chunks, Neo4j Cypher/templates, entity resolve | **Weak — priority** |
| 3 | **Compliance Specialist** | Which clauses / evidence gaps apply? | clause library, gap map, evidence levels | **Partial** (compliance pkg, not agentized) |
| 4 | **RCA / Maintenance Specialist** | Similar failures, WO patterns, manuals | CMMS/WO, failure codes, sensor history, manuals | **Missing** |
| 5 | **Lessons Specialist** | Push proactive lesson cards when live context matches past | embeddings + rule features vs RiskContext | **Missing** |
| 6 | **Multimodal Spotter** (optional) | Interpret radio+frame together for the brief | Melia transcript, vision detections, frame URI | **Build light** |

**Count for summit narrative:** **1 orchestrator + 4–5 specialists** (telemetry, knowledge, compliance, RCA, lessons). Not 20 autonomous bots.

---

## 5. GenAI leverage map (paid stack we already own)

| Asset | Underused today | Best leverage |
|---|---|---|
| **aimlapi** | Mostly ask + investigator + PPE VLM | Orchestrator + specialists + structured JSON + translate + eval judges |
| **Cognee** | Often disabled | Always-on cognify; memory tools for Knowledge Specialist; episodic finding close |
| **Speechmatics Melia** | Newly wired | Canonical `voice-event` + English ops text feeding Knowledge + Investigator |
| **Neo4j** | Sync/hooks thin | GraphRAG templates: Document–MENTIONS→Equipment–IN→Zone–HAS→Permit |
| **Docling / docintel** | Text path OK | Page-level chunks with citations into Knowledge Specialist |
| **Vision** | Parallel to agents | Spotter tools: last detections for zone on finding |

---

## 6. Decisions (locked for the plan)

1. **Keep P1.** No LLM inside `verge_risk` evaluation.  
2. **Promote advisory GenAI** to a first-class phase track (not a thin Phase 3 afterthought).  
3. **Replace “one investigator forever”** with **orchestrator + specialists**, reusing the existing tool-loop code.  
4. **GraphRAG required** for Living Knowledge DoD (Cognee + Neo4j), not chunk-only chat.  
5. **Validator layer** before any barrier recommendation is shown as “recommended” (vs “hypothesis”).  
6. **Agent eval harness** with gold briefs (groundedness, citation precision, no-invented-tags).  
7. **Stay framework-sovereign** (our loop); do not take a LangChain dependency for summit.  
8. **Knowledge → Live Risk** only as **canonical facts/events** (`voice-event`, `procedure_gap`, `open_capa`), never free-text LLM into the engine.

---

## 7. Plan deltas (what changes in the roadmap)

### Immediate (next engineering weeks) — **Phase 2.5 GenAI Core**
Insert before/overlapping late Phase 2:

| Work | Outcome |
|---|---|
| Cognee always-on for ingest + memory tools | Knowledge Specialist has real memory |
| Neo4j GraphRAG query templates + tool | Multi-hop citations |
| Split Investigator → Orchestrator + Telemetry/Knowledge/Compliance specialists | Modern agent shape |
| Deterministic brief validator | No invented equipment tags / zones |
| Multimodal tools on finding (voice transcript + vision events) | Summit “one moment” story |
| `eval/agents/` gold briefs | Claims are measurable |

### Phase 3 (reframed)
- RCA / Lessons become **specialists** under the same orchestrator, not isolated demoware.  
- Compliance agent = Compliance Specialist + gap UI (already partly built).  

### Explicitly deferred
- LLM-in-the-loop control / FTC execution (research-interesting; wrong for our P8 summit claim).  
- Paying for another agent cloud.

---

## 8. Success metrics (GenAI usefulness)

| Metric | Target |
|---|---|
| Investigator/orchestrator groundedness on gold set | ≥ 0.90 |
| Citation precision | ≥ 0.85 |
| Invented tag rate (equipment/zone not in twin) | **0** on gold set |
| Time-to-brief (p50) | < 20s with warm Cognee |
| Degraded path | Fact sheet always available without LLM |
| Safety import lint | `verge_risk` still cannot import `verge_llm` |

---

## 9. Bottom line

We do **not** need to “become more agentic” by letting GenAI run the plant.  
We need to become more agentic by letting GenAI **investigate like a senior safety engineer with a library and a radio** — with GraphRAG, specialists, validators, and evals — while the **risk engine stays boring and lethal-correct**.

That is the modern industrial GenAI posture in 2026, and it matches Verge’s thesis better than a single chat panel.
