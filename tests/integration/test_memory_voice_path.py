from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_memory_voice_full_http_path(monkeypatch) -> None:
    def fake_query(query, *, finding=None):
        return {
            "answer": f"answer for {query}",
            "citations": [{"id": "stub", "title": "Stub", "excerpt": "mocked Cognee"}],
            "degraded": False,
            "finding": finding.finding_id if finding else None,
        }

    def fake_near_miss(audio, *, filename, content_type, finding_id=None):
        return {
            "kind": "voice-near-miss",
            "findingId": finding_id,
            "transcript": "mocked Speechmatics transcript",
            "structured": {
                "summary": "mocked",
                "hazards": ["gas"],
                "zones": ["B-04"],
                "actions": [],
            },
            "degraded": False,
            "provider": "speechmatics",
        }

    monkeypatch.setattr("verge_api.routes.memory.query_memory", fake_query)
    monkeypatch.setattr("verge_api.routes.voice.near_miss_from_audio", fake_near_miss)

    memory = client.post(
        "/api/memory/query",
        json={"query": "what should Maya check?", "findingId": "F-CONV-07"},
    )
    assert memory.status_code == 200
    assert memory.json()["degraded"] is False
    assert memory.json()["finding"] == "F-CONV-07"

    voice = client.post(
        "/api/voice/near-miss",
        data={"actor": "maya", "findingId": "F-CONV-07"},
        files={"file": ("near-miss.wav", b"audio", "audio/wav")},
    )
    assert voice.status_code == 200
    assert voice.json()["degraded"] is False
    assert voice.json()["structured"]["hazards"] == ["gas"]
