"""Live fusion evaluate — voice + hot-work permit → finding."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_schema.events import VoiceEvent


def test_fuse_voice_hot_work() -> None:
    client = TestClient(app)
    app.state.voice_events = [
        VoiceEvent(
            event_id="VE-TEST",
            ts=datetime.now(UTC),
            transcript="gas smell near battery B-04",
            zone_id="B-04",
            hazards=["gas", "smell"],
            source="radio",
        )
    ]
    # Demo seed usually includes a hot-work permit in B-04.
    r = client.post("/api/risk/fuse", json={"persist": False})
    assert r.status_code == 200
    body = r.json()
    assert "findings" in body
    assert body["inputs"]["voiceEvents"] >= 1
    titles = [f["title"].lower() for f in body["findings"]]
    assert any("radio-reported gas" in t for t in titles), titles
