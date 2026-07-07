"""Sensor reading ingest and finding telemetry routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from verge_contracts.envelope import ContractViolation, validate_and_enrich

from .. import metrics_counters
from ..stream_notify import drain_outbox
from ..telemetry import telemetry_for_finding
from ..timescale_writer import maybe_write_timescale, timescale_status
from ..trace import current_trace_id

router = APIRouter(tags=["readings"])


class ReadingIngestBody(BaseModel):
    type: str = "reading"
    ts: str
    sensorId: str
    kind: str
    unit: str
    zoneId: str
    value: float
    eventId: str | None = None
    siteId: str | None = None


@router.post("/readings/ingest")
def ingest_reading(body: ReadingIngestBody, request: Request) -> dict:
    """Ingest a canonical reading event (live path from risk-engine or sim)."""
    raw = body.model_dump(exclude_none=True)
    try:
        payload = validate_and_enrich(raw, trace_id=current_trace_id())
    except ContractViolation as exc:
        metrics_counters.contract_rejections += 1
        raise HTTPException(422, {"errors": exc.result.errors}) from exc

    skip_redpanda = request.headers.get("X-Verge-Skip-Republish", "").lower() in {
        "1", "true", "yes",
    }

    buf = request.app.state.readings
    buf.ingest(payload)
    ts_result = maybe_write_timescale(payload)
    if not ts_result.get("written") and ts_result.get("configured"):
        metrics_counters.timescale_write_failures += 1
    elif ts_result.get("written"):
        metrics_counters.timescale_writes += 1

    store = request.app.state.store
    if hasattr(store, "enqueue_reading"):
        store.enqueue_reading(payload, skip_redpanda=skip_redpanda)
    drain_outbox(request.app)

    return {
        "ok": True,
        "sensorId": payload["sensorId"],
        "eventId": payload.get("eventId"),
        "timescale": ts_result,
        "outboxPending": getattr(store, "outbox_pending", lambda: 0)(),
    }


@router.get("/timescale/status")
def timescale_status_route() -> dict:
    """Timescale hypertable probe for plant IT and the console."""
    return timescale_status()


@router.get("/findings/{finding_id}/telemetry")
def finding_telemetry(finding_id: str, request: Request) -> dict:
    """Time-series for sensors linked to a finding (lineage + zone fallback)."""
    store = request.app.state.store
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    thresholds = getattr(request.app.state, "sensor_thresholds", {})
    return telemetry_for_finding(
        request.app.state.readings,
        finding,
        thresholds=thresholds,
    )
