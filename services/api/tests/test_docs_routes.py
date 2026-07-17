"""Document ingest + grounded knowledge ask."""

from __future__ import annotations

from fastapi.testclient import TestClient
from verge_api.main import app


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


def test_ask_empty_corpus_is_honest() -> None:
    # Assert contract on empty ask shape by clearing docintel.
    client = TestClient(app)
    from verge_docintel import DocIntelStore

    app.state.docintel = DocIntelStore()
    r = client.post("/api/knowledge/ask", json={"query": "anything about pumps?"})
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert body["citations"] == []
    assert body["answer"] == ""
