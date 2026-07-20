"""In-process voice audio clips for console playback (Live Ops).

Transcription consumes bytes once; we keep a small rolling map so
``GET /api/voice/clips/{event_id}`` can play the same radio clip honestly.
"""

from __future__ import annotations

_MAX_CLIPS = 48


def _map(app_state) -> dict[str, tuple[bytes, str]]:
    m = getattr(app_state, "voice_clip_bytes", None)
    if m is None:
        app_state.voice_clip_bytes = {}
        m = app_state.voice_clip_bytes
    return m


def store_clip(
    app_state,
    event_id: str,
    audio: bytes,
    *,
    content_type: str = "audio/wav",
) -> str:
    """Store bytes; return the browser-fetchable API path."""
    if not event_id or not audio:
        return ""
    m = _map(app_state)
    m[event_id] = (audio, content_type or "application/octet-stream")
    while len(m) > _MAX_CLIPS:
        oldest = next(iter(m))
        del m[oldest]
    return f"/api/voice/clips/{event_id}"


def get_clip(app_state, event_id: str) -> tuple[bytes, str] | None:
    return _map(app_state).get(event_id)


def clip_uri_if_present(app_state, event_id: str) -> str | None:
    if get_clip(app_state, event_id) is None:
        return None
    return f"/api/voice/clips/{event_id}"
