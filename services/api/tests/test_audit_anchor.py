"""Signed audit-head anchoring tests."""

from __future__ import annotations

from verge_api.audit_anchor import (
    build_anchor_doc,
    sign_head,
    verify_anchored_head,
    verify_signature,
)


class _FakeStore:
    def __init__(self, head: str = "abc123", entries: int = 5) -> None:
        self._head = head
        self._entries = entries

    def audit_head(self) -> str:
        return self._head

    def audit_len(self) -> int:
        return self._entries


def test_sign_and_verify_head() -> None:
    doc = {
        "siteId": "demo-site",
        "head": "deadbeef",
        "entries": 10,
        "signature": sign_head(head="deadbeef", site_id="demo-site", entries=10, secret="s3cr3t"),
        "algorithm": "hmac-sha256",
    }
    assert verify_signature(doc, secret="s3cr3t")
    assert not verify_signature(doc, secret="wrong")


def test_build_anchor_doc_requires_secret() -> None:
    store = _FakeStore()
    assert build_anchor_doc(store=store, env={}) is None
    doc = build_anchor_doc(store=store, env={"VERGE_AUDIT_ANCHOR_SECRET": "k"})
    assert doc
    assert doc["head"] == "abc123"
    assert verify_signature(doc, secret="k")


def test_verify_anchored_head_without_object_store() -> None:
    store = _FakeStore()
    status = verify_anchored_head(store, env={"VERGE_AUDIT_ANCHOR_SECRET": "k"})
    assert status["configured"] is True
    assert status["anchored"] is False
    assert status["matches"] is None
