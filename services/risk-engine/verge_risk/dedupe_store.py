"""Durable dedupe state for the streaming risk engine (audit §2).

Persists emitted finding keys so restarts do not re-alert the same convergence.
File-backed JSON — good enough for single-worker pilot; partition-safe store
would be RocksDB/Redpanda state store at fleet scale.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class DedupeStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else None
        self._seen: set[str] = set()
        if self._path and self._path.exists():
            self._load()

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> DedupeStore:
        env = env or dict(os.environ)
        path = env.get("VERGE_DEDUPE_STATE")
        return cls(path)

    def _load(self) -> None:
        if self._path is None:
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._seen = set(data.get("keys", []))

    def save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"keys": sorted(self._seen)}, indent=2)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self._path)

    def seen(self, key: tuple[str, tuple[str, ...]]) -> bool:
        token = self._token(key)
        return token in self._seen

    def remember(self, key: tuple[str, tuple[str, ...]]) -> None:
        self._seen.add(self._token(key))

    @staticmethod
    def _token(key: tuple[str, tuple[str, ...]]) -> str:
        zone, lineage = key
        return f"{zone}|{'|'.join(lineage)}"

    def __len__(self) -> int:
        return len(self._seen)
