"""Rolling voice-event buffer for risk-engine fusion predicates."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from verge_schema.events import VoiceEvent

_MAX = 200
_ZONE_RE = re.compile(r"\b([A-Z]-\d{2,})\b")
_HAZARD_LEXICON = (
    "gas",
    "lel",
    "smell",
    "flammable",
    "h2s",
    "toxic",
    "smoke",
    "fire",
    "leak",
)


def _events(app_state) -> list[VoiceEvent]:
    buf = getattr(app_state, "voice_events", None)
    if buf is None:
        app_state.voice_events = []
        buf = app_state.voice_events
    return buf


def record_voice_event(
    app_state,
    *,
    transcript: str,
    structured: dict | None = None,
    zone_id: str | None = None,
    source: str = "radio",
    ts: datetime | None = None,
) -> VoiceEvent:
    structured = structured or {}
    hazards = [str(h).lower() for h in (structured.get("hazards") or [])]
    zones = [str(z) for z in (structured.get("zones") or [])]
    if not hazards:
        low = transcript.lower()
        hazards = [h for h in _HAZARD_LEXICON if h in low]
    if not zone_id:
        zone_id = zones[0] if zones else None
    if not zone_id:
        m = _ZONE_RE.search(transcript.upper())
        zone_id = m.group(1) if m else None
    ev = VoiceEvent(
        event_id=f"VE-{uuid.uuid4().hex[:10].upper()}",
        ts=ts or datetime.now(UTC),
        transcript=transcript,
        zone_id=zone_id,
        hazards=hazards,
        equipment_ids=[str(x) for x in (structured.get("equipment") or [])],
        source=source,
    )
    buf = _events(app_state)
    buf.append(ev)
    del buf[:-_MAX]
    return ev


def list_voice_events(app_state, *, limit: int = 50) -> list[VoiceEvent]:
    buf = _events(app_state)
    cap = max(1, min(limit, _MAX))
    return list(reversed(buf[-cap:]))
