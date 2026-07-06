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
