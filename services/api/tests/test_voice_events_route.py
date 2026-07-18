"""Voice event ingest for risk fusion."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_api.voice_events import VoiceEventBuffer


def test_voice_event_text_ingest() -> None:
    client = TestClient(app)
    app.state.voice_event_buffer = VoiceEventBuffer(engine=None)
    app.state.voice_events = app.state.voice_event_buffer.events
    r = client.post(
        "/api/voice/events",
        json={
            "transcript": "gas smell near battery B-04, pause hot work",
            "zoneId": "B-04",
            "source": "radio",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["event"]["zoneId"] == "B-04"
    assert "gas" in [h.lower() for h in body["event"]["hazards"]]
    assert "cognee" in body
    assert "fusion" in body  # None when VERGE_VOICE_AUTO_FUSE=false in unit tests

    listed = client.get("/api/voice/events").json()
    assert listed["count"] >= 1


def test_voice_event_feeds_fuse_predicate() -> None:
    client = TestClient(app)
    app.state.voice_event_buffer = VoiceEventBuffer(engine=None)
    app.state.voice_events = app.state.voice_event_buffer.events
    r = client.post(
        "/api/voice/events",
        json={
            "transcript": "gas smell near battery B-04",
            "zoneId": "B-04",
            "source": "radio",
            "hazards": ["gas", "smell"],
        },
    )
    assert r.status_code == 200
    fuse = client.post("/api/risk/fuse", json={"persist": False})
    assert fuse.status_code == 200
    body = fuse.json()
    assert body["inputs"]["voiceEvents"] >= 1
    titles = [f["title"].lower() for f in body["findings"]]
    assert any("radio-reported gas" in t for t in titles), titles
