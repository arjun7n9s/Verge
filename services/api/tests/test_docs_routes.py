"""Document ingest + grounded knowledge ask (DocIntel + optional Cognee hybrid)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_docintel import DocIntelStore


def test_ingest_and_ask_grounded() -> None:
    client = TestClient(app)
    content = (
        b"Hot Work SOP\n\n"
        b"Before welding near LEL-04 in B-04, confirm permit PW-0142 and isolate P-3.\n"
        b"Reference OISD-STD-105.\n"
    )
    r = client.post(
        "/api/docs/ingest",
        files={"file": ("hot-work-sop.md", content, "text/markdown")},
        data={"title": "Hot Work SOP"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["document"]["status"] == "ready"
    assert body["entityCount"] >= 1
    assert body["chunkCount"] >= 1
    assert body["resolvedEntityCount"] >= 1
    assert "hooks" in body
    assert "cognee" in body["hooks"]
    assert "neo4j" in body["hooks"]

    listed = client.get("/api/docs").json()
    assert listed["count"] >= 1

    ask = client.post(
        "/api/knowledge/ask",
        json={"query": "What to check before hot work in B-04?"},
    )
    assert ask.status_code == 200
    result = ask.json()
    assert result["citations"]
    assert result["answer"]
    assert "docintel" in (result.get("sources") or [])


def test_ask_empty_corpus_is_honest() -> None:
    client = TestClient(app)
    app.state.docintel = DocIntelStore()
    r = client.post("/api/knowledge/ask", json={"query": "anything about pumps?"})
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert body["citations"] == []
    assert body["answer"] == ""


def test_ask_hybrid_merges_cognee_citations(monkeypatch) -> None:
    client = TestClient(app)
    content = (
        b"Hot Work SOP\n\n"
        b"Before welding near LEL-04 in B-04, confirm permit PW-0142.\n"
    )
    client.post(
        "/api/docs/ingest",
        files={"file": ("hot-work-sop.md", content, "text/markdown")},
        data={"title": "Hot Work SOP"},
    )

    def fake_cognee(query, *, llm, limit):
        return (
            [
                {
                    "documentId": "cognee-1",
                    "title": "Plant memory",
                    "chunkId": None,
                    "page": None,
                    "excerpt": "LEL below 10% LEL required before hot work in B-04.",
                    "score": 0,
                    "source": "cognee",
                }
            ],
            {"degraded": False, "reason": "", "narrativeDegraded": True, "answer": ""},
        )

    monkeypatch.setattr("verge_api.routes.docs._cognee_citations", fake_cognee)
    ask = client.post(
        "/api/knowledge/ask",
        json={"query": "What to check before hot work in B-04?"},
    )
    assert ask.status_code == 200
    result = ask.json()
    sources = set(result.get("sources") or [])
    assert "docintel" in sources
    assert "cognee" in sources
    assert any(c.get("source") == "cognee" for c in result["citations"])


def test_ask_cognee_only_when_docintel_empty(monkeypatch) -> None:
    client = TestClient(app)
    app.state.docintel = DocIntelStore()

    def fake_cognee(query, *, llm, limit):
        return (
            [
                {
                    "documentId": "cognee-1",
                    "title": "Near-miss memory",
                    "chunkId": None,
                    "page": None,
                    "excerpt": "Gas smell radio report linked to B-04 hot work pause.",
                    "score": 0,
                    "source": "cognee",
                }
            ],
            {
                "degraded": False,
                "reason": "",
                "narrativeDegraded": False,
                "answer": "Pause hot work when radio reports gas near B-04 [1].",
            },
        )

    monkeypatch.setattr("verge_api.routes.docs._cognee_citations", fake_cognee)
    ask = client.post(
        "/api/knowledge/ask",
        json={"query": "What did radio say about B-04?"},
    )
    assert ask.status_code == 200
    result = ask.json()
    assert result["degraded"] is False
    assert result["sources"] == ["cognee"]
    assert "Pause hot work" in result["answer"]
