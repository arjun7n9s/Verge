"""Voice audio clip cache for Live Ops playback."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_voice_clip_store_and_serve():
    from verge_api.audio_clip_cache import store_clip
    from verge_api.main import app
    from verge_api.voice_events import record_voice_event

    client = TestClient(app)
    ev = record_voice_event(
        app.state,
        transcript="Gas smell near B-04",
        zone_id="B-04",
        source="radio",
    )
    wav = b"RIFF" + b"\x00" * 24 + b"WAVE" + b"\x00" * 32
    path = store_clip(app.state, ev.event_id, wav, content_type="audio/wav")
    assert path == f"/api/voice/clips/{ev.event_id}"

    r = client.get(path)
    assert r.status_code == 200
    assert r.content == wav
    assert "audio" in r.headers["content-type"]

    listed = client.get("/api/voice/events?limit=5").json()
    hit = next(e for e in listed["events"] if e["eventId"] == ev.event_id)
    assert hit["audioClipUri"] == path


def test_voice_clip_missing_404():
    from verge_api.main import app

    client = TestClient(app)
    assert client.get("/api/voice/clips/VE-MISSING").status_code == 404
