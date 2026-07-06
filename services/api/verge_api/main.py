"""Verge API gateway (spec §2 plane 5).

SSE/WebSocket fan-out, findings + lifecycle, feedback, sensor ribbon, and a
degradation-aware /health that reflects the §10.6 contract (the LLM can be down;
the safety core and the API are not).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from verge_llm import provider_from_env
from verge_orchestrator import respond
from verge_risk.health import ribbon as health_ribbon  # noqa: F401 (kept in sync)
from verge_schema.enums import FeedbackVerdict
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding
from verge_schema.lifecycle import IllegalTransition
from verge_twin import load_plant
from verge_twin.plant import DEMO_PLANT

from .auth import AuthMiddleware
from .evidence_store import upload_evidence_manifest
from .factory import make_store
from .hooks import maybe_ingest_closed_finding, maybe_ingest_feedback
from .routes.evidence import router as evidence_router
from .routes.fleet import router as fleet_router
from .routes.memory import router as memory_router
from .routes.permits import router as permits_router
from .routes.plant import router as plant_router
from .routes.readings import router as readings_router
from .routes.reports import router as reports_router
from .routes.voice import router as voice_router
from .seed import seed
from .state_factory import make_permits_registry, make_reading_buffer

app = FastAPI(title="Verge API", version="0.3.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.add_middleware(AuthMiddleware)
app.include_router(fleet_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(plant_router, prefix="/api")
app.include_router(readings_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(permits_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# Backend from VERGE_STORE (memory default; sql persists). Seed only when empty
# so a durable store keeps its history across restarts.
store = make_store()
app.state.store = store
app.state.permits = make_permits_registry(store=store)
llm = provider_from_env()
app.state.llm = llm
if not store.list_findings(shadow=None):
    seed(store)
app.state.permits.seed_demo(datetime.now(UTC))

_demo_plant = load_plant(DEMO_PLANT)
app.state.readings = make_reading_buffer(store=store)
app.state.readings.seed_from_replay()
app.state.sensor_thresholds = _demo_plant.thresholds_by_kind()


class TransitionBody(BaseModel):
    to: S
    actor: str
    reasonCode: str | None = None
    reasonText: str | None = None


class FeedbackBody(BaseModel):
    actor: str
    verdict: FeedbackVerdict
    reasonCode: str | None = None


@app.get("/health")
def health() -> dict:
    """Liveness + degradation posture. The API stays healthy even when the LLM
    narrative layer is degraded (P1, §10.6)."""
    return {
        "status": "ok",
        "llm": {"provider": llm.name, "degraded": not llm.healthy()},
        "audit": {
            "entries": store.audit_len(),
            "head": store.audit_head(),
            "verified": store.audit_verify(),
        },
        "findings": len(store.list_findings(shadow=None)),
    }


@app.get("/api/findings")
def list_findings(state: str | None = None, shadow: bool = False) -> list[dict]:
    """The operator feed. shadow=False (default) returns live findings only;
    shadow=True returns the shadow-review surface (spec §14.5)."""
    return [f.model_dump(by_alias=True, mode="json") for f in store.list_findings(state, shadow)]


@app.get("/api/shadow/summary")
def shadow_summary() -> dict:
    """Day-31 shadow-mode readout: how much Verge would have flagged."""
    return store.shadow_summary()


@app.post("/api/findings")
def ingest_finding(finding: RiskFinding) -> dict:
    """Ingest a finding from the streaming risk-engine (the live path) so it
    appears on the console. Idempotent on finding_id."""
    store.add_finding(finding)
    return finding.model_dump(by_alias=True, mode="json")


@app.get("/api/findings/{finding_id}")
def get_finding(finding_id: str) -> dict:
    f = store.get_finding(finding_id)
    if not f:
        raise HTTPException(404, "finding not found")
    return f.model_dump(by_alias=True, mode="json")


@app.post("/api/findings/{finding_id}/transition")
def transition_finding(finding_id: str, body: TransitionBody) -> dict:
    if store.get_finding(finding_id) is None:
        raise HTTPException(404, "finding not found")
    try:
        f = store.transition(finding_id, body.to, body.actor, body.reasonCode, body.reasonText)
    except IllegalTransition as e:
        raise HTTPException(409, str(e)) from e
    maybe_ingest_closed_finding(f, to=body.to)
    return f.model_dump(by_alias=True, mode="json")


@app.post("/api/findings/{finding_id}/feedback")
def feedback(finding_id: str, body: FeedbackBody) -> dict:
    if store.get_finding(finding_id) is None:
        raise HTTPException(404, "finding not found")
    fb = store.add_feedback(finding_id, body.actor, body.verdict, body.reasonCode)
    f = store.get_finding(finding_id)
    if f:
        maybe_ingest_feedback(
            f,
            verdict=body.verdict.value,
            reason_code=body.reasonCode,
            reason_text=getattr(body, "reasonText", None),
        )
    return {"feedback": fb.model_dump(by_alias=True, mode="json"), "fpr": store.fpr()}


@app.post("/api/findings/{finding_id}/respond")
def respond_to_finding(finding_id: str) -> dict:
    """Draft the coordinated response (Act 3): advisory action + multilingual
    alert + evidence pack + report draft. Verge executes nothing (P8); it
    hash-chains the recommendation and returns it for the operator to Approve."""
    f = store.get_finding(finding_id)
    if not f:
        raise HTTPException(404, "finding not found")
    r = respond(f, at=datetime.now(UTC), provider=llm)
    for payload in r.audit_payloads():
        store.audit_append(
            actor="orchestrator", kind=payload["kind"], payload=payload,
            timestamp=datetime.now(UTC),
        )
    object_store = upload_evidence_manifest(r.evidence)
    return {
        "action": r.action.model_dump(by_alias=True, mode="json"),
        "alert": r.alert.model_dump(by_alias=True, mode="json"),
        "evidence": {
            **r.evidence.model_dump(by_alias=True, mode="json"),
            "objectStore": object_store,
        },
        "report": {
            "markdown": r.report.markdown,
            "cited": r.report.cited,
            "submitted": r.report.submitted,
            "narrativeDegraded": r.report.narrative_degraded,
        },
    }


@app.get("/api/sensors/ribbon")
def sensor_ribbon() -> dict:
    health = store.get_sensor_health()
    counts = {q.value: n for q, n in health.items()}
    return {"text": health_ribbon(health), "counts": counts}


@app.get("/api/audit")
def audit(limit: int = 50) -> list[dict]:
    return store.audit_entries(limit)


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    """Server-Sent Events: push the current findings snapshot every 2s. A real
    deployment fans out from Redpanda; this is enough for the console + demo."""

    async def gen():
        while True:
            payload = [f.model_dump(by_alias=True, mode="json") for f in store.list_findings()]
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(2.0)

    return StreamingResponse(gen(), media_type="text/event-stream")
