"""Live fusion evaluate — sensors + permits + voice + vision → findings."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from verge_risk import STARTER_RULES, evaluate, load_rules
from verge_risk.context import RiskContext
from verge_schema.core import Reading, Sensor
from verge_schema.events import VisionDetection, VoiceEvent

router = APIRouter(tags=["fusion"])


class FuseBody(BaseModel):
    persist: bool = False
    inChangeover: bool = False
    limit: int = Field(default=50, ge=1, le=200)


def _sensors_and_readings(buf) -> tuple[dict[str, Sensor], dict[str, list[Reading]]]:
    sensors: dict[str, Sensor] = {}
    readings: dict[str, list[Reading]] = {}
    for sid, points in getattr(buf, "_by_sensor", {}).items():
        if not points:
            continue
        last = points[-1]
        sensors[sid] = Sensor(
            sensor_id=sid,
            kind=str(last.get("kind") or "unknown"),
            unit=str(last.get("unit") or ""),
            zone_id=str(last.get("zoneId") or "UNKNOWN"),
            expected_cadence_s=30.0,
            plausible_min=0.0,
            plausible_max=1e6,
        )
        series: list[Reading] = []
        for p in points:
            try:
                ts = datetime.fromisoformat(str(p["ts"]).replace("Z", "+00:00"))
            except ValueError:
                continue
            # SQLite often returns naive timestamps; risk health compares to UTC now.
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            series.append(Reading(sensor_id=sid, ts=ts, value=float(p["value"])))
        if series:
            readings[sid] = series
    return sensors, readings


def run_live_fusion(
    app_state,
    *,
    persist: bool = False,
    in_changeover: bool = False,
    limit: int = 50,
) -> dict:
    """Evaluate starter rules against live buffers (LLM-free, P1)."""
    now = datetime.now(UTC)
    plant = app_state.plant
    sensors, readings = _sensors_and_readings(app_state.readings)
    for sid, node in plant.sensors.items():
        sensors.setdefault(
            sid,
            Sensor(
                sensor_id=sid,
                kind=node.kind,
                unit=node.unit,
                zone_id=node.zone_id,
                expected_cadence_s=node.cadence_s,
                plausible_min=0.0,
                plausible_max=1e6,
            ),
        )
    permits = app_state.permits.list_active(now=now)
    voice = list(getattr(app_state, "voice_events", []) or [])[-limit:]
    vision = list(getattr(app_state, "vision_detections", []) or [])[-limit:]
    voice_events = [
        v if isinstance(v, VoiceEvent) else VoiceEvent.model_validate(v) for v in voice
    ]
    vision_dets = [
        v if isinstance(v, VisionDetection) else VisionDetection.model_validate(v)
        for v in vision
    ]
    ctx = RiskContext(
        now=now,
        sensors=sensors,
        readings=readings,
        permits=permits,
        thresholds=dict(app_state.sensor_thresholds or plant.thresholds_by_kind()),
        in_changeover=in_changeover,
        voice_events=voice_events,
        vision_detections=vision_dets,
    )
    findings = evaluate(ctx, load_rules(STARTER_RULES))
    persisted = 0
    if persist:
        store = app_state.store
        for f in findings:
            store.add_finding(f)
            persisted += 1
    return {
        "count": len(findings),
        "persisted": persisted,
        "inputs": {
            "sensors": len(sensors),
            "readings": sum(len(v) for v in readings.values()),
            "permits": len(permits),
            "voiceEvents": len(voice_events),
            "visionDetections": len(vision_dets),
            "inChangeover": in_changeover,
        },
        "findings": [f.model_dump(by_alias=True, mode="json") for f in findings],
    }


@router.post("/risk/fuse")
def fuse_evaluate(body: FuseBody, request: Request) -> dict:
    """Evaluate starter rules against live buffers (voice/vision/permits/readings).

    LLM-free (P1). Returns findings with lineage; optional persist into the store.
    """
    return run_live_fusion(
        request.app.state,
        persist=body.persist,
        in_changeover=body.inChangeover,
        limit=body.limit,
    )
