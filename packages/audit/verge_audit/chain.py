"""The hash chain itself.

hash(entry) = sha256( prev_hash || canonical(entry-without-hash) )

`canonical_json` is a stable serialization (sorted keys, no insignificant
whitespace) so the same logical entry always hashes identically across
processes and languages.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from datetime import datetime
from typing import Any

GENESIS_HASH = "0" * 64


def canonical_json(payload: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, ISO datetimes."""

    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"not JSON-serializable: {type(o)!r}")

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=default)


def hash_entry(prev_hash: str, body: dict[str, Any]) -> str:
    """Hash an entry body against the previous hash. `body` must NOT contain
    `hash` (the field we are computing) -- include everything else that is
    covered by the chain (entry_id, timestamp, actor, kind, payload, prev_hash)."""

    material = prev_hash + canonical_json(body)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class AuditEntry:
    """Plain record. (verge_schema.AuditEntry mirrors this on the wire.)"""

    __slots__ = ("entry_id", "timestamp", "actor", "kind", "payload", "hash", "prev_hash")

    def __init__(
        self,
        entry_id: str,
        timestamp: datetime,
        actor: str,
        kind: str,
        payload: dict[str, Any],
        prev_hash: str,
    ) -> None:
        self.entry_id = entry_id
        self.timestamp = timestamp
        self.actor = actor
        self.kind = kind
        self.payload = payload
        self.prev_hash = prev_hash
        self.hash = hash_entry(prev_hash, self._body())

    def _body(self) -> dict[str, Any]:
        return {
            "entryId": self.entry_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "kind": self.kind,
            "payload": self.payload,
            "prevHash": self.prev_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        d = self._body()
        d["hash"] = self.hash
        return d


class IntegrityError(Exception):
    """Raised when the chain fails to re-verify (spec §10.6 audit-corruption row)."""

    def __init__(self, index: int, message: str) -> None:
        self.index = index
        super().__init__(f"audit chain integrity failed at block {index}: {message}")


class AuditChain:
    """In-memory hash chain. Persistence layers wrap this; the invariant is here."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    @property
    def head(self) -> str:
        return self._entries[-1].hash if self._entries else GENESIS_HASH

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[AuditEntry]:
        return iter(self._entries)

    def append(
        self,
        actor: str,
        kind: str,
        payload: dict[str, Any],
        timestamp: datetime,
        entry_id: str | None = None,
    ) -> AuditEntry:
        entry_id = entry_id or f"AE-{len(self._entries):08d}"
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            actor=actor,
            kind=kind,
            payload=payload,
            prev_hash=self.head,
        )
        self._entries.append(entry)
        return entry

    def verify(self) -> None:
        """Walk the chain; raise IntegrityError at the first broken link."""
        prev = GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.prev_hash != prev:
                raise IntegrityError(i, "prev_hash does not match preceding head")
            recomputed = hash_entry(entry.prev_hash, entry._body())
            if recomputed != entry.hash:
                raise IntegrityError(i, "recomputed hash does not match stored hash")
            prev = entry.hash

    @classmethod
    def from_entries(cls, rows: Iterable[dict[str, Any]]) -> AuditChain:
        """Rebuild from persisted rows and verify (used by snapshot restore)."""
        return cls.from_persisted(rows)

    @classmethod
    def from_persisted(cls, rows: Iterable[dict[str, Any]]) -> AuditChain:
        """Rebuild using persisted hash columns — catches partial DB tampering."""
        from datetime import datetime

        chain = cls()
        for i, r in enumerate(rows):
            ts = r["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            body = {
                "entryId": r["entryId"],
                "timestamp": ts,
                "actor": r["actor"],
                "kind": r["kind"],
                "payload": r["payload"],
                "prevHash": r["prevHash"],
            }
            prev_hash = r["prevHash"]
            stored_hash = r.get("hash")
            recomputed = hash_entry(prev_hash, body)
            if stored_hash is not None and stored_hash != recomputed:
                raise IntegrityError(i, "persisted hash does not match recomputed body")
            entry = AuditEntry(
                entry_id=r["entryId"],
                timestamp=ts,
                actor=r["actor"],
                kind=r["kind"],
                payload=r["payload"],
                prev_hash=prev_hash,
            )
            if stored_hash is not None and entry.hash != stored_hash:
                raise IntegrityError(i, "stored hash column mismatch")
            chain._entries.append(entry)
        chain.verify()
        return chain
