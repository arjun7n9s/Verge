"""Voice transcription routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, Request, UploadFile
from verge_voice import alert_preview, near_miss_from_audio, transcribe_audio

router = APIRouter(tags=["voice"])
VOICE_FILE = File(...)
ACTOR_FORM = Form("operator")
FINDING_FORM = Form(None)


@router.post("/voice/transcribe")
async def voice_transcribe(file: UploadFile = VOICE_FILE) -> dict:
    audio = await file.read()
    result = transcribe_audio(
        audio,
        filename=file.filename or "handover.wav",
        content_type=file.content_type or "application/octet-stream",
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
    )
    request.app.state.store.audit_append(
        actor=actor,
        kind="voice-near-miss",
        payload=dict(body),
        timestamp=datetime.now(UTC),
    )
    body["auditAppended"] = True
    return body


@router.post("/findings/{finding_id}/alert/preview")
def finding_alert_preview(finding_id: str, request: Request) -> dict:
    from fastapi import HTTPException

    finding = request.app.state.store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    return alert_preview(finding, provider=request.app.state.llm)
