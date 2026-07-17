"""Voice event ingest for risk fusion."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app


def test_voice_event_text_ingest() -> None:
    client = TestClient(app)
    app.state.voice_events = []
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

    listed = client.get("/api/voice/events").json()
    assert listed["count"] >= 1
