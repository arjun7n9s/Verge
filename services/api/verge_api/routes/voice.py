"""Voice transcription routes — Melia → English ops → events + Cognee."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from verge_voice import (
    PLANT_RADIO_HINTS_DEFAULT,
    UNSUPPORTED_PLANT_REQUESTS,
    alert_preview,
    melia_language_catalog,
    near_miss_from_audio,
    near_miss_from_transcript,
    transcribe_audio,
)

from ..audio_clip_cache import get_clip, store_clip
from ..hooks import maybe_ingest_near_miss, maybe_ingest_voice_ops
from ..voice_events import list_voice_events, record_voice_event

_TRUE = {"1", "true", "yes", "on"}

router = APIRouter(tags=["voice"])
VOICE_FILE = File(...)
ACTOR_FORM = Form("operator")
FINDING_FORM = Form(None)


class VoiceEventBody(BaseModel):
    transcript: str = Field(min_length=2)
    zoneId: str | None = None
    source: str = "radio"
    hazards: list[str] = Field(default_factory=list)


def _english_ops(result) -> str:
    """Canonical English ops text from a VoiceResult / dict."""
    if hasattr(result, "transcript_en") and result.transcript_en:
        return result.transcript_en
    if hasattr(result, "transcript"):
        return result.transcript or ""
    if isinstance(result, dict):
        return result.get("transcriptEn") or result.get("transcript") or ""
    return ""


def _guess_audio_type(filename: str | None, content_type: str | None) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct.startswith("audio/") or ct == "application/ogg":
        return ct
    name = (filename or "").lower()
    if name.endswith(".wav"):
        return "audio/wav"
    if name.endswith(".mp3"):
        return "audio/mpeg"
    if name.endswith(".ogg"):
        return "audio/ogg"
    if name.endswith(".webm"):
        return "audio/webm"
    if name.endswith(".m4a"):
        return "audio/mp4"
    return "audio/wav"


def _attach_clip(app_state, ev, audio: bytes, *, filename: str | None, content_type: str | None):
    uri = store_clip(
        app_state,
        ev.event_id,
        audio,
        content_type=_guess_audio_type(filename, content_type),
    )
    if uri:
        ev.audio_clip_uri = uri
    return ev


def _record_from_voice_result(app_state, result, *, source: str, zone_id: str | None = None):
    english = _english_ops(result)
    structured = result.structured if hasattr(result, "structured") else {}
    original = getattr(result, "transcript_original", None)
    langs = list(getattr(result, "languages_detected", ()) or ())
    zones = structured.get("zones") or []
    zid = zone_id or (zones[0] if zones else None)
    return record_voice_event(
        app_state,
        transcript=english,
        structured=structured,
        zone_id=zid,
        source=source,
        transcript_original=original if original and original != english else None,
        languages_detected=langs,
    )


def _maybe_fuse_after_voice(app_state, *, structured: dict | None = None) -> dict | None:
    """Run LLM-free fusion after radio evidence lands (preview; persist opt-in)."""
    flag = os.environ.get("VERGE_VOICE_AUTO_FUSE", "true").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return None
    structured = structured or {}
    hazards = structured.get("hazards") or []
    try:
        from .fusion import run_live_fusion

        persist = os.environ.get("VERGE_VOICE_AUTO_FUSE_PERSIST", "false").lower() in _TRUE
        out = run_live_fusion(app_state, persist=persist, limit=50)
        return {
            "count": out.get("count", 0),
            "persisted": out.get("persisted", 0),
            "findingIds": [
                f.get("findingId") for f in (out.get("findings") or []) if f.get("findingId")
            ][:12],
            "hazardsSeen": list(hazards)[:8],
        }
    except Exception as exc:  # noqa: BLE001
        return {"count": 0, "persisted": 0, "reason": f"fuse:{type(exc).__name__}"}


@router.get("/voice/languages")
def voice_languages() -> dict:
    """Melia-supported languages + plant-radio hints (honest about gaps)."""
    return {
        "model": "melia-1",
        "mode": "batch",
        "languages": melia_language_catalog(),
        "count": len(melia_language_catalog()),
        "plantRadioHints": list(PLANT_RADIO_HINTS_DEFAULT),
        "unsupportedPlantRequests": [
            {"code": code, "note": note}
            for code, note in UNSUPPORTED_PLANT_REQUESTS.items()
        ],
        "notes": [
            "Melia auto-detects and code-switches; set language=multi in job config.",
            "Speechmatics Melia does not include translation_config — Verge "
            "translates to English via aimlapi when non-English is detected.",
            "Telugu (te) and Kannada (kn) are not in the current Melia table.",
        ],
    }


@router.post("/voice/transcribe")
async def voice_transcribe(request: Request, file: UploadFile = VOICE_FILE) -> dict:
    audio = await file.read()
    result = transcribe_audio(
        audio,
        filename=file.filename or "handover.wav",
        content_type=file.content_type or "application/octet-stream",
        provider=request.app.state.llm,
    )
    body = result.to_dict()
    if not result.degraded and _english_ops(result).strip():
        ev = _record_from_voice_result(request.app.state, result, source="transcribe")
        _attach_clip(
            request.app.state,
            ev,
            audio,
            filename=file.filename,
            content_type=file.content_type,
        )
        body["voiceEventId"] = ev.event_id
        body["audioClipUri"] = ev.audio_clip_uri
        body["cognee"] = maybe_ingest_voice_ops(
            _english_ops(result),
            structured=result.structured,
            source="transcribe",
        )
        body["fusion"] = _maybe_fuse_after_voice(
            request.app.state, structured=result.structured
        )
    return body


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
    english = _english_ops(result)
    payload = {
        "kind": "voice-handover",
        "actor": actor,
        "transcript": english,
        "transcriptOriginal": result.transcript_original,
        "structured": result.structured,
        "degraded": result.degraded,
        "reason": result.reason,
        "provider": result.provider,
        "jobId": result.job_id,
        "languagesDetected": list(result.languages_detected or ()),
    }
    request.app.state.store.audit_append(
        actor=actor,
        kind="voice-handover",
        payload=payload,
        timestamp=datetime.now(UTC),
    )
    body = result.to_dict()
    body["auditAppended"] = True
    if not result.degraded and english.strip():
        ev = _record_from_voice_result(request.app.state, result, source="handover")
        _attach_clip(
            request.app.state,
            ev,
            audio,
            filename=file.filename,
            content_type=file.content_type,
        )
        body["voiceEventId"] = ev.event_id
        body["audioClipUri"] = ev.audio_clip_uri
        body["cognee"] = maybe_ingest_voice_ops(
            english, structured=result.structured, source="handover"
        )
        body["fusion"] = _maybe_fuse_after_voice(
            request.app.state, structured=result.structured
        )
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
    english = body.get("transcriptEn") or body.get("transcript", "")
    structured = body.get("structured") or {}
    body["auditAppended"] = True
    if english.strip():
        cognee = maybe_ingest_near_miss(
            english,
            structured=structured,
            finding_id=findingId,
        )
        ev = record_voice_event(
            request.app.state,
            transcript=english,
            structured=structured,
            source="near-miss",
            transcript_original=body.get("transcriptOriginal"),
            languages_detected=body.get("languagesDetected") or [],
        )
        _attach_clip(
            request.app.state,
            ev,
            audio,
            filename=file.filename,
            content_type=file.content_type,
        )
        body["voiceEventId"] = ev.event_id
        body["audioClipUri"] = ev.audio_clip_uri
        body["cognee"] = cognee
        body["fusion"] = _maybe_fuse_after_voice(
            request.app.state, structured=structured
        )
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
    cognee = maybe_ingest_voice_ops(
        body.transcript, structured=structured, source=body.source
    )
    fusion = _maybe_fuse_after_voice(request.app.state, structured=structured)
    request.app.state.store.audit_append(
        actor="operator",
        kind="voice-event",
        payload=ev.model_dump(by_alias=True, mode="json"),
        timestamp=datetime.now(UTC),
    )
    return {
        "event": ev.model_dump(by_alias=True, mode="json"),
        "cognee": cognee,
        "fusion": fusion,
    }


@router.get("/voice/events")
def voice_events_recent(request: Request, limit: int = 50) -> dict:
    events = list_voice_events(request.app.state, limit=limit)
    return {
        "events": [e.model_dump(by_alias=True, mode="json") for e in events],
        "count": len(events),
    }


@router.get("/voice/clips/{event_id}")
def voice_clip_bytes(event_id: str, request: Request) -> Response:
    hit = get_clip(request.app.state, event_id)
    if hit is None:
        from fastapi import HTTPException

        raise HTTPException(404, "audio clip not in cache")
    data, content_type = hit
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "no-store", "X-Verge-Voice-Event": event_id},
    )


@router.post("/findings/{finding_id}/alert/preview")
def finding_alert_preview(finding_id: str, request: Request) -> dict:
    from fastapi import HTTPException

    finding = request.app.state.store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    return alert_preview(finding, provider=request.app.state.llm)
