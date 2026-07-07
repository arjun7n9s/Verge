"""Sensor reading ingest and finding telemetry routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..stream_notify import notify_reading
from ..timescale_writer import maybe_write_timescale

router = APIRouter(tags=["readings"])


class ReadingIngestBody(BaseModel):
    type: str = "reading"
    ts: str
    sensorId: str
    kind: str
    unit: str
    zoneId: str
    value: float


@router.post("/readings/ingest")
def ingest_reading(body: ReadingIngestBody, request: Request) -> dict:
    """Ingest a canonical reading event (live path from risk-engine or sim)."""
    buf = request.app.state.readings
    payload = body.model_dump()
    buf.ingest(payload)
    maybe_write_timescale(payload)
    notify_reading(request.app, payload)
    return {"ok": True, "sensorId": body.sensorId}


@router.get("/findings/{finding_id}/telemetry")
def finding_telemetry(finding_id: str, request: Request) -> dict:
    """Time-series for sensors linked to a finding (lineage + zone fallback)."""
    store = request.app.state.store
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    thresholds = getattr(request.app.state, "sensor_thresholds", {})
    return request.app.state.readings.series_for_finding(finding, thresholds=thresholds)
