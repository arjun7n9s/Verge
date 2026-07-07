"""Verge API gateway (spec §2 plane 5).

SSE/WebSocket fan-out, findings + lifecycle, feedback, sensor ribbon, and a
degradation-aware /health that reflects the §10.6 contract (the LLM can be down;
the safety core and the API are not).
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from verge_llm import provider_from_env
from verge_mlops import DEMO_REGISTRY, ModelRegistry
from verge_orchestrator import respond
from verge_risk.health import ribbon as health_ribbon  # noqa: F401 (kept in sync)
from verge_schema.enums import FeedbackVerdict
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding
from verge_schema.lifecycle import IllegalTransition
from verge_twin import load_plant
from verge_twin.plant import DEMO_PLANT
from verge_vision import provider_from_env as vision_provider_from_env

from .auth import AuthMiddleware
from .evidence_store import upload_evidence_manifest
from .factory import make_store
from .hooks import maybe_ingest_closed_finding, maybe_ingest_feedback
from .ops import ops_snapshot, render_prometheus
from .routes.alerts import router as alerts_router
from .routes.commission import router as commission_router
from .routes.compliance import router as compliance_router
from .routes.degradation import router as degradation_router
from .routes.eval_report import router as eval_report_router
from .routes.evidence import router as evidence_router
from .routes.fleet import router as fleet_router
from .routes.memory import router as memory_router
from .routes.models import router as models_router
from .routes.ops import router as ops_router
from .routes.permits import router as permits_router
from .routes.plant import router as plant_router
from .routes.plant_graph import router as plant_graph_router
from .routes.readings import router as readings_router
from .routes.reports import router as reports_router
from .routes.vision import router as vision_router
from .routes.voice import router as voice_router
from .seed import seed
from .state_factory import make_permits_registry, make_reading_buffer


def _load_model_registry() -> ModelRegistry:
    """A writable registry at VERGE_MODEL_REGISTRY, else the read-only demo."""
    path = os.environ.get("VERGE_MODEL_REGISTRY")
    if path and Path(path).exists():
        return ModelRegistry(path)
    return ModelRegistry.read_only(DEMO_REGISTRY)


app = FastAPI(title="Verge API", version="0.3.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.add_middleware(AuthMiddleware)
app.include_router(fleet_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(commission_router, prefix="/api")
app.include_router(compliance_router, prefix="/api")
app.include_router(eval_report_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(plant_router, prefix="/api")
app.include_router(plant_graph_router, prefix="/api")
app.include_router(readings_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(vision_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(ops_router, prefix="/api")
app.include_router(degradation_router, prefix="/api")
app.include_router(permits_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# Backend from VERGE_STORE (memory default; sql persists). Seed only when empty
# so a durable store keeps its history across restarts.
store = make_store()
app.state.store = store
app.state.permits = make_permits_registry(store=store)
llm = provider_from_env()
app.state.llm = llm
app.state.vision = vision_provider_from_env()
app.state.model_registry = _load_model_registry()
app.state.started_at = datetime.now(UTC)
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


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    """Prometheus scrape for plant IT (spec §14.6). Distinct from the operator
    console; dependency-free text exposition format."""
    snap = ops_snapshot(
        store=store, readings=app.state.readings, llm=llm, vision=app.state.vision,
        version=app.version, started_at=app.state.started_at,
    )
    return render_prometheus(snap)


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
