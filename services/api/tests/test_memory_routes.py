from fastapi.testclient import TestClient
from verge_api.main import app

client = TestClient(app)


def test_memory_context_degrades_when_cognee_unconfigured() -> None:
    r = client.get("/api/findings/F-CONV-07/context")
    assert r.status_code == 200
    body = r.json()
    assert body["findingId"] == "F-CONV-07"
    assert body["degraded"] is True
    assert body["similarIncidents"] == []
    assert body["regulatoryClauses"] == []
    assert body["plantHistory"] == []


def test_memory_context_unknown_finding_is_404() -> None:
    assert client.get("/api/findings/NOPE/context").status_code == 404


def test_memory_query_degrades_when_cognee_unconfigured() -> None:
    r = client.post(
        "/api/memory/query",
        json={"query": "what should Maya check?", "findingId": "F-CONV-07"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert body["answer"] == ""
    assert body["citations"] == []


def test_memory_query_unknown_finding_is_404() -> None:
    r = client.post("/api/memory/query", json={"query": "anything", "findingId": "NOPE"})
    assert r.status_code == 404
