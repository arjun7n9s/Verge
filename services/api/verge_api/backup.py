"""Backup + restore verification for the audit chain (spec §14.6).

The audit chain is the most legally-sensitive artifact in the system, so a
restore is not trusted until it is **replayed and re-verified**: rebuild the
chain from the snapshot rows and walk the hashes; any linkage break or head
mismatch rejects the snapshot (P6, §14.6). The plant keeps the returned
verification report as evidence the restore is sound.

Rebuilding uses the same :class:`verge_audit.AuditChain` invariant as the live
store — one definition of "valid chain", exercised on both the hot path and on
restore.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from verge_audit import canonical_json
from verge_audit.chain import AuditChain, IntegrityError

# Big enough to snapshot the whole chain (the store caps reads by this arg).
_ALL = 10_000_000


def _canonical_ts(ts: object) -> object:
    """Normalize a timestamp to the isoformat the chain hashed with.

    A snapshot serialized to JSON (e.g. by FastAPI) renders a tz-aware datetime
    as ``…Z``, but the live chain hashed it via ``datetime.isoformat()`` (``…+00:00``).
    Reparsing to a datetime makes the recomputed hash format-independent, so a
    restore verifies regardless of how the snapshot was written."""
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return ts
    return ts


def _normalize(entries: list[dict]) -> list[dict]:
    return [{**e, "timestamp": _canonical_ts(e.get("timestamp"))} for e in entries]


def _snapshot_hash(entries: list[dict]) -> str:
    return hashlib.sha256(canonical_json(_normalize(entries)).encode("utf-8")).hexdigest()


def snapshot_audit(store) -> dict:
    """Export the full audit chain as a verifiable snapshot."""
    entries = store.audit_entries(limit=_ALL)
    return {
        "entries": entries,
        "count": len(entries),
        "head": store.audit_head(),
        "snapshotHash": _snapshot_hash(entries),
    }


def verify_snapshot(snapshot: dict, *, expected_head: str | None = None) -> dict:
    """Replay a snapshot's hash chain; reject on any mismatch (§14.6).

    The chain is rebuilt and its linkage re-walked, and the recomputed head is
    checked against the head recorded *in* the snapshot and its content hash.
    That detects accidental corruption and partial edits (a payload changed
    without fixing downstream hashes).

    It does NOT, by itself, defeat a *fully re-forged* chain — an adversary who
    rebuilds every hash consistently and rewrites the recorded head/snapshotHash
    passes, because those fields travel inside the snapshot. To anchor trust,
    pass ``expected_head`` — a head recorded out-of-band (a signed
    restore-verification report, or the live store's head): the recomputed head
    must then also equal that trusted value. Without it, treat a pass as
    "internally consistent", not "provably authentic"."""
    entries = snapshot.get("entries", [])
    rows = [
        {
            "entryId": e["entryId"],
            "timestamp": _canonical_ts(e["timestamp"]),
            "actor": e["actor"],
            "kind": e["kind"],
            "payload": e["payload"],
            "prevHash": e["prevHash"],
        }
        for e in entries
    ]
    try:
        chain = AuditChain.from_entries(rows)  # rebuilds + verifies linkage
    except IntegrityError as e:
        return {
            "verified": False,
            "reason": str(e),
            "block": e.index,
            "entries": len(entries),
        }
    except (KeyError, TypeError) as e:
        return {"verified": False, "reason": f"malformed snapshot: {e}", "entries": len(entries)}

    head_matches = chain.head == snapshot.get("head")
    recomputed_hash = _snapshot_hash(entries)
    hash_matches = recomputed_hash == snapshot.get("snapshotHash")
    # If an out-of-band trusted head is supplied, the recomputed head must match
    # it — this is what makes verification proof-of-authenticity, not just
    # proof-of-internal-consistency.
    anchor_matches = expected_head is None or chain.head == expected_head
    verified = head_matches and hash_matches and anchor_matches
    reason = ""
    if not verified:
        if not anchor_matches:
            reason = "recomputed head does not match the trusted expected_head"
        else:
            reason = "recomputed head or content hash does not match snapshot"
    return {
        "verified": verified,
        "entries": len(entries),
        "head": chain.head,
        "headMatches": head_matches,
        "snapshotHash": recomputed_hash,
        "snapshotHashMatches": hash_matches,
        "anchored": expected_head is not None,
        "anchorMatches": anchor_matches,
        "reason": reason,
    }
