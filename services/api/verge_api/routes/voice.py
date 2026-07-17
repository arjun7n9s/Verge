"""Voice transcription routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from verge_voice import (
    alert_preview,
    near_miss_from_audio,
    near_miss_from_transcript,
    transcribe_audio,
)

from ..hooks import maybe_ingest_near_miss
from ..voice_events import list_voice_events, record_voice_event

router = APIRouter(tags=["voice"])
VOICE_FILE = File(...)
ACTOR_FORM = Form("operator")
FINDING_FORM = Form(None)


class VoiceEventBody(BaseModel):
    transcript: str = Field(min_length=2)
    zoneId: str | None = None
    source: str = "radio"
    hazards: list[str] = Field(default_factory=list)


@router.post("/voice/transcribe")
async def voice_transcribe(request: Request, file: UploadFile = VOICE_FILE) -> dict:
    audio = await file.read()
    result = transcribe_audio(
        audio,
        filename=file.filename or "handover.wav",
        content_type=file.content_type or "application/octet-stream",
        provider=request.app.state.llm,
    )
    return result.to_dict()


@router.post("/voice/handover")
async def voice_handover(
    request: Request,
    file: UploadFile = VOICE_FILE,
    actor: str = ACTOR_FORM,
) -> dict:
    audio = await file.read()
    result = transcribe_audio(
        audio,
        filename=file.filename or "handover.wav",
        content_type=file.content_type or "application/octet-stream",
        provider=request.app.state.llm,
    )
    payload = {
        "kind": "voice-handover",
        "actor": actor,
        "transcript": result.transcript,
        "structured": result.structured,
        "degraded": result.degraded,
        "reason": result.reason,
        "provider": result.provider,
        "jobId": result.job_id,
    }
    request.app.state.store.audit_append(
        actor=actor,
        kind="voice-handover",
        payload=payload,
        timestamp=datetime.now(UTC),
    )
    body = result.to_dict()
    body["auditAppended"] = True
    return body


@router.get("/voice/handover/recent")
def voice_handover_recent(request: Request, limit: int = 20) -> list[dict]:
    """Recent shift handover transcripts (from durable audit log)."""
    cap = max(1, min(limit, 100))
    entries = request.app.state.store.audit_entries(limit=500)
    handovers = [e for e in entries if e.get("kind") == "voice-handover"]
    out: list[dict] = []
    for entry in handovers[-cap:]:
        payload = entry.get("payload") or {}
        out.append(
            {
                "entryId": entry.get("entryId"),
                "timestamp": entry.get("timestamp"),
                "actor": entry.get("actor") or payload.get("actor"),
                "transcript": payload.get("transcript", ""),
                "structured": payload.get("structured"),
                "degraded": payload.get("degraded", False),
                "provider": payload.get("provider"),
            }
        )
    return list(reversed(out))


@router.post("/voice/near-miss")
async def voice_near_miss(
    request: Request,
    file: UploadFile = VOICE_FILE,
    actor: str = ACTOR_FORM,
    findingId: str | None = FINDING_FORM,
) -> dict:
    audio = await file.read()
    if findingId and request.app.state.store.get_finding(findingId) is None:
        from fastapi import HTTPException

        raise HTTPException(404, "finding not found")
    body = near_miss_from_audio(
        audio,
        filename=file.filename or "near-miss.wav",
        content_type=file.content_type or "application/octet-stream",
        finding_id=findingId,
        provider=request.app.state.llm,
    )
    request.app.state.store.audit_append(
        actor=actor,
        kind="voice-near-miss",
        payload=dict(body),
        timestamp=datetime.now(UTC),
    )
    maybe_ingest_near_miss(
        body.get("transcript", ""),
        structured=body.get("structured") or {},
        finding_id=findingId,
    )
    ev = record_voice_event(
        request.app.state,
        transcript=body.get("transcript", ""),
        structured=body.get("structured") or {},
        source="near-miss",
    )
    body["auditAppended"] = True
    body["voiceEventId"] = ev.event_id
    return body


@router.post("/voice/events")
def voice_event_ingest(body: VoiceEventBody, request: Request) -> dict:
    """Ingest a structured voice/radio event (text path for drills & demos)."""
    structured = {"hazards": body.hazards, "zones": [body.zoneId] if body.zoneId else []}
    if not body.hazards:
        structured = near_miss_from_transcript(body.transcript).get("structured") or structured
    ev = record_voice_event(
        request.app.state,
        transcript=body.transcript,
        structured=structured,
        zone_id=body.zoneId,
        source=body.source,
    )
    request.app.state.store.audit_append(
        actor="operator",
        kind="voice-event",
        payload=ev.model_dump(by_alias=True, mode="json"),
        timestamp=datetime.now(UTC),
    )
    return {"event": ev.model_dump(by_alias=True, mode="json")}


@router.get("/voice/events")
def voice_events_recent(request: Request, limit: int = 50) -> dict:
    events = list_voice_events(request.app.state, limit=limit)
    return {
        "events": [e.model_dump(by_alias=True, mode="json") for e in events],
        "count": len(events),
    }


@router.post("/findings/{finding_id}/alert/preview")
def finding_alert_preview(finding_id: str, request: Request) -> dict:
    from fastapi import HTTPException

    finding = request.app.state.store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    return alert_preview(finding, provider=request.app.state.llm)
