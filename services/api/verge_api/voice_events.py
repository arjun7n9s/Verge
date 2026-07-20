"""Rolling voice-event buffer for risk-engine fusion (optional SQL durability)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, insert, select
from sqlalchemy.engine import Engine
from verge_schema.events import VoiceEvent

from . import db

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


class VoiceEventBuffer:
    """In-memory ring with optional SQL persist/hydrate (same pattern as readings)."""

    def __init__(self, engine: Engine | None = None, max_events: int = _MAX) -> None:
        self._max = max_events
        self._engine = engine
        self.events: list[VoiceEvent] = []
        if engine is not None:
            self._hydrate_from_db()

    def _hydrate_from_db(self) -> None:
        try:
            with self._engine.begin() as conn:  # type: ignore[union-attr]
                rows = conn.execute(
                    select(db.voice_event).order_by(db.voice_event.c.ts.asc())
                ).mappings().all()
        except Exception:
            return
        for row in rows:
            langs = row.get("languages_detected") or []
            hazards = row.get("hazards") or []
            equipment = row.get("equipment_ids") or []
            ts = row["ts"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            ev = VoiceEvent(
                event_id=row["event_id"],
                ts=ts,
                transcript=row.get("transcript") or "",
                transcript_original=row.get("transcript_original"),
                languages_detected=list(langs),
                zone_id=row.get("zone_id"),
                hazards=list(hazards),
                equipment_ids=list(equipment),
                source=row.get("source") or "radio",
                audio_clip_uri=None,
            )
            self.events.append(ev)
        if len(self.events) > self._max:
            del self.events[: -self._max]

    def _persist(self, ev: VoiceEvent) -> None:
        if self._engine is None:
            return
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    insert(db.voice_event).values(
                        event_id=ev.event_id,
                        ts=ev.ts,
                        transcript=ev.transcript,
                        transcript_original=ev.transcript_original,
                        languages_detected=list(ev.languages_detected or []),
                        zone_id=ev.zone_id,
                        hazards=list(ev.hazards or []),
                        equipment_ids=list(ev.equipment_ids or []),
                        source=ev.source,
                    )
                )
                rows = conn.execute(
                    select(db.voice_event.c.event_id).order_by(db.voice_event.c.ts.desc())
                ).scalars().all()
                if len(rows) > self._max:
                    stale = rows[self._max :]
                    conn.execute(
                        delete(db.voice_event).where(db.voice_event.c.event_id.in_(stale))
                    )
        except Exception:
            return

    def record(
        self,
        *,
        transcript: str,
        structured: dict | None = None,
        zone_id: str | None = None,
        source: str = "radio",
        ts: datetime | None = None,
        transcript_original: str | None = None,
        languages_detected: list[str] | None = None,
        audio_clip_uri: str | None = None,
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
            transcript_original=transcript_original,
            languages_detected=list(languages_detected or []),
            zone_id=zone_id,
            hazards=hazards,
            equipment_ids=[str(x) for x in (structured.get("equipment") or [])],
            source=source,
            audio_clip_uri=audio_clip_uri,
        )
        self.events.append(ev)
        del self.events[: -self._max]
        self._persist(ev)
        self._sync_neo4j(ev)
        return ev

    def _sync_neo4j(self, ev: VoiceEvent) -> None:
        """Best-effort KG link; never raises into the voice ingest path."""
        try:
            from verge_twin.voice_graph import sync_voice_event

            sync_voice_event(ev)
        except Exception:
            return

    def list_recent(self, *, limit: int = 50) -> list[VoiceEvent]:
        cap = max(1, min(limit, self._max))
        return list(reversed(self.events[-cap:]))


def _buffer(app_state) -> VoiceEventBuffer:
    buf = getattr(app_state, "voice_event_buffer", None)
    if isinstance(buf, VoiceEventBuffer):
        return buf
    # Legacy / tests: ensure a list exists and wrap without SQL.
    events = getattr(app_state, "voice_events", None)
    if events is None:
        app_state.voice_events = []
        events = app_state.voice_events
    wrapper = VoiceEventBuffer(engine=None)
    wrapper.events = events
    app_state.voice_event_buffer = wrapper
    return wrapper


def record_voice_event(
    app_state,
    *,
    transcript: str,
    structured: dict | None = None,
    zone_id: str | None = None,
    source: str = "radio",
    ts: datetime | None = None,
    transcript_original: str | None = None,
    languages_detected: list[str] | None = None,
    audio_clip_uri: str | None = None,
) -> VoiceEvent:
    buf = _buffer(app_state)
    # Keep app.state.voice_events pointing at the same list fusion reads.
    app_state.voice_events = buf.events
    return buf.record(
        transcript=transcript,
        structured=structured,
        zone_id=zone_id,
        source=source,
        ts=ts,
        transcript_original=transcript_original,
        languages_detected=languages_detected,
        audio_clip_uri=audio_clip_uri,
    )


def list_voice_events(app_state, *, limit: int = 50) -> list[VoiceEvent]:
    from .audio_clip_cache import clip_uri_if_present

    buf = _buffer(app_state)
    app_state.voice_events = buf.events
    events = buf.list_recent(limit=limit)
    # Attach clip URI when bytes are still in the rolling cache (P4 — no invent).
    out: list[VoiceEvent] = []
    for ev in events:
        uri = ev.audio_clip_uri or clip_uri_if_present(app_state, ev.event_id)
        if uri and uri != ev.audio_clip_uri:
            out.append(ev.model_copy(update={"audio_clip_uri": uri}))
        else:
            out.append(ev)
    return out
