"""Document post-ingest hooks degrade cleanly when backends are off."""

from __future__ import annotations

from datetime import UTC, datetime

from verge_api.doc_hooks import maybe_cognify_document, maybe_sync_entities_neo4j
from verge_docintel.pipeline import DocIntelStore
from verge_schema.documents import DocumentAsset, DocumentKind, DocumentStatus


def test_cognee_hook_disabled(monkeypatch) -> None:
    monkeypatch.setenv("VERGE_COGNEE_ENABLED", "false")
    monkeypatch.setenv("COGNEE_API_KEY", "k")
    monkeypatch.setenv("COGNEE_BASE_URL", "https://api.cognee.ai")
    store = DocIntelStore()
    asset = DocumentAsset(
        document_id="DOC-1",
        title="t",
        kind=DocumentKind.SOP,
        status=DocumentStatus.READY,
        created_at=datetime.now(UTC),
    )
    store.texts["DOC-1"] = "hello"
    out = maybe_cognify_document(store, asset)
    assert out["degraded"] is True
    assert out["reason"] == "cognee-disabled"


def test_cognee_hook_auto_on_with_keys(monkeypatch) -> None:
    monkeypatch.delenv("VERGE_COGNEE_ENABLED", raising=False)
    monkeypatch.setenv("COGNEE_API_KEY", "k")
    monkeypatch.setenv("COGNEE_BASE_URL", "https://api.cognee.ai")
    monkeypatch.setenv("VERGE_SITE_ID", "test")
    calls: list[str] = []

    class FakeClient:
        settings = type("S", (), {"ready": True, "missing_reason": lambda self: None})()

        @staticmethod
        def from_env(env):
            return FakeClient()

    def fake_ingest(client, dataset, title, text, *, ensure_dataset=True):
        calls.append(title)
        return type("R", (), {"degraded": False, "reason": "", "status_code": 200})()

    monkeypatch.setattr("verge_api.doc_hooks.CogneeClient", FakeClient)
    monkeypatch.setattr("verge_api.doc_hooks.ingest_and_cognify", fake_ingest)
    store = DocIntelStore()
    asset = DocumentAsset(
        document_id="DOC-1",
        title="Hot Work SOP",
        kind=DocumentKind.SOP,
        status=DocumentStatus.READY,
        created_at=datetime.now(UTC),
    )
    store.texts["DOC-1"] = "purge before hot work in B-04"
    out = maybe_cognify_document(store, asset)
    assert out["degraded"] is False
    assert calls == ["Hot Work SOP"]


def test_neo4j_hook_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    store = DocIntelStore()
    asset = DocumentAsset(
        document_id="DOC-1",
        title="t",
        kind=DocumentKind.SOP,
        status=DocumentStatus.READY,
        created_at=datetime.now(UTC),
    )
    out = maybe_sync_entities_neo4j(store, asset)
    assert out["degraded"] is True
    assert out["reason"] == "neo4j-unconfigured"
