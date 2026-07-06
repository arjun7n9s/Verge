from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_voice_transcribe_degrades_without_key() -> None:
    r = client.post(
        "/api/voice/transcribe",
        files={"file": ("handover.wav", b"audio", "audio/wav")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert body["transcript"] == ""


def test_voice_handover_appends_audit_even_when_degraded() -> None:
    before = len(client.get("/api/audit?limit=999").json())
    r = client.post(
        "/api/voice/handover",
        data={"actor": "maya"},
        files={"file": ("handover.wav", b"audio", "audio/wav")},
    )
    assert r.status_code == 200
    assert r.json()["auditAppended"] is True
    after = client.get("/api/audit?limit=999").json()
    assert len(after) == before + 1
    assert after[-1]["kind"] == "voice-handover"


def test_voice_handover_recent_lists_audit_entries() -> None:
    client.post(
        "/api/voice/handover",
        data={"actor": "maya"},
        files={"file": ("handover.wav", b"audio", "audio/wav")},
    )
    r = client.get("/api/voice/handover/recent?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["actor"] == "maya"
    assert "transcript" in body[0]


def test_voice_near_miss_appends_audit_even_when_degraded() -> None:
    before = len(client.get("/api/audit?limit=999").json())
    r = client.post(
        "/api/voice/near-miss",
        data={"actor": "maya", "findingId": "F-CONV-07"},
        files={"file": ("near-miss.wav", b"audio", "audio/wav")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["auditAppended"] is True
    assert body["kind"] == "voice-near-miss"
    assert body["findingId"] == "F-CONV-07"
    after = client.get("/api/audit?limit=999").json()
    assert len(after) == before + 1
    assert after[-1]["kind"] == "voice-near-miss"


def test_voice_near_miss_unknown_finding_is_404() -> None:
    r = client.post(
        "/api/voice/near-miss",
        data={"findingId": "NOPE"},
        files={"file": ("near-miss.wav", b"audio", "audio/wav")},
    )
    assert r.status_code == 404


def test_alert_preview_template_fallback() -> None:
    r = client.post("/api/findings/F-CONV-07/alert/preview")
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert "en" in body["languages"]
    assert "hi" in body["languages"]
