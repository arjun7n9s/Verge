"""Durable dedupe state for streaming risk engine."""

from __future__ import annotations

from pathlib import Path

from verge_risk.dedupe_store import DedupeStore


def test_dedupe_store_persists_keys(tmp_path: Path) -> None:
    path = tmp_path / "dedupe.json"
    store = DedupeStore(path)
    key = ("B-04", ("reading:LEL-04",))
    store.remember(key)
    store.save()

    reloaded = DedupeStore(path)
    assert reloaded.seen(key)
    assert len(reloaded) == 1


def test_dedupe_store_in_memory_without_path() -> None:
    store = DedupeStore()
    key = ("Z-1", ("a",))
    store.remember(key)
    assert store.seen(key)
    store.save()  # no-op without path
