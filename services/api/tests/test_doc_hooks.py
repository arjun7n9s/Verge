"""Document post-ingest hooks degrade cleanly when backends are off."""

from __future__ import annotations

from datetime import UTC, datetime

from verge_api.doc_hooks import maybe_cognify_document, maybe_sync_entities_neo4j
from verge_docintel.pipeline import DocIntelStore
from verge_schema.documents import DocumentAsset, DocumentKind, DocumentStatus


def test_cognee_hook_disabled(monkeypatch) -> None:
    monkeypatch.setenv("VERGE_COGNEE_ENABLED", "false")
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
