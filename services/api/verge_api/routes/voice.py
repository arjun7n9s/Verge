"""Voice transcription routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, Request, UploadFile
from verge_voice import transcribe_audio

router = APIRouter(tags=["voice"])
VOICE_FILE = File(...)
ACTOR_FORM = Form("operator")


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
