"""Signed audit-head anchoring to object storage (audit §3, §14.6).

The hash chain catches local tampering, but a DB actor can re-forge a consistent
chain. Anchoring the head out-of-band with an HMAC signature stored in MinIO
(WORM bucket in production) gives restore verification a trusted reference.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
from datetime import UTC, datetime
from typing import Any

ALGORITHM = "hmac-sha256"


def _site_id(env: dict[str, str]) -> str:
    return env.get("VERGE_SITE_ID", "demo-site")


def _anchor_secret(env: dict[str, str]) -> str | None:
    secret = env.get("VERGE_AUDIT_ANCHOR_SECRET") or env.get("MINIO_SECRET_KEY")
    return secret or None


def _minio_settings(env: dict[str, str]) -> dict[str, str | bool] | None:
    endpoint = env.get("MINIO_ENDPOINT")
    access = env.get("MINIO_ACCESS_KEY")
    secret = env.get("MINIO_SECRET_KEY")
    if not endpoint or not access or not secret:
        return None
    return {
        "endpoint": endpoint.replace("http://", "").replace("https://", ""),
        "access": access,
        "secret": secret,
        "bucket": env.get("MINIO_BUCKET_AUDIT", "verge-audit"),
        "secure": env.get("MINIO_USE_SSL", "false").lower() in {"1", "true", "yes"},
    }


def sign_head(*, head: str, site_id: str, entries: int, secret: str) -> str:
    material = f"{site_id}|{entries}|{head}".encode()
    return hmac.new(secret.encode(), material, hashlib.sha256).hexdigest()


def verify_signature(doc: dict, *, secret: str) -> bool:
    expected = sign_head(
        head=str(doc.get("head", "")),
        site_id=str(doc.get("siteId", "")),
        entries=int(doc.get("entries", 0)),
        secret=secret,
    )
    return hmac.compare_digest(expected, str(doc.get("signature", "")))


def build_anchor_doc(*, store, env: dict[str, str] | None = None) -> dict[str, Any] | None:
    env = env or dict(os.environ)
    secret = _anchor_secret(env)
    if not secret:
        return None
    head = store.audit_head()
    entries = store.audit_len()
    site = _site_id(env)
    return {
        "siteId": site,
        "head": head,
        "entries": entries,
        "algorithm": ALGORITHM,
        "signature": sign_head(head=head, site_id=site, entries=entries, secret=secret),
        "anchoredAt": datetime.now(UTC).isoformat(),
    }


def _anchor_key(site_id: str) -> str:
    return f"anchors/{site_id}/latest.json"


def write_anchor(doc: dict, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Persist anchor document to MinIO; return metadata."""
    env = env or dict(os.environ)
    cfg = _minio_settings(env)
    if cfg is None:
        return {"anchored": False, "reason": "MINIO_* not configured"}
    try:
        from minio import Minio
    except ImportError:
        return {"anchored": False, "reason": "minio package not installed"}

    body = json.dumps(doc, indent=2, sort_keys=True).encode("utf-8")
    key = _anchor_key(str(doc["siteId"]))
    try:
        client = Minio(
            str(cfg["endpoint"]),
            access_key=str(cfg["access"]),
            secret_key=str(cfg["secret"]),
            secure=bool(cfg["secure"]),
        )
        bucket = str(cfg["bucket"])
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        client.put_object(
            bucket, key, io.BytesIO(body), len(body), content_type="application/json",
        )
        return {"anchored": True, "bucket": bucket, "key": key, "head": doc["head"]}
    except Exception as exc:
        return {"anchored": False, "reason": type(exc).__name__}


def read_anchor(*, env: dict[str, str] | None = None) -> dict[str, Any] | None:
    env = env or dict(os.environ)
    cfg = _minio_settings(env)
    if cfg is None:
        return None
    try:
        from minio import Minio
    except ImportError:
        return None
    site = _site_id(env)
    key = _anchor_key(site)
    try:
        client = Minio(
            str(cfg["endpoint"]),
            access_key=str(cfg["access"]),
            secret_key=str(cfg["secret"]),
            secure=bool(cfg["secure"]),
        )
        obj = client.get_object(str(cfg["bucket"]), key)
        try:
            return json.loads(obj.read().decode("utf-8"))
        finally:
            obj.close()
            obj.release_conn()
    except Exception:
        return None


def anchor_audit_head(store, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Sign and upload the current audit head."""
    env = env or dict(os.environ)
    doc = build_anchor_doc(store=store, env=env)
    if doc is None:
        return {"anchored": False, "reason": "VERGE_AUDIT_ANCHOR_SECRET not configured"}
    result = write_anchor(doc, env=env)
    return {**result, "document": doc}


def verify_anchored_head(store, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Compare live chain head against the last signed anchor."""
    env = env or dict(os.environ)
    secret = _anchor_secret(env)
    if not secret:
        return {"configured": False, "matches": None, "reason": "anchor secret not configured"}

    live_head = store.audit_head()
    live_entries = store.audit_len()
    doc = read_anchor(env=env)
    if doc is None:
        return {
            "configured": True,
            "matches": None,
            "anchored": False,
            "liveHead": live_head,
            "reason": "no anchor document in object store",
        }
    sig_ok = verify_signature(doc, secret=secret)
    head_ok = doc.get("head") == live_head
    entries_ok = int(doc.get("entries", -1)) <= live_entries
    return {
        "configured": True,
        "anchored": True,
        "signatureValid": sig_ok,
        "headMatches": head_ok,
        "entriesMonotonic": entries_ok,
        "matches": sig_ok and head_ok and entries_ok,
        "liveHead": live_head,
        "anchoredHead": doc.get("head"),
        "anchoredAt": doc.get("anchoredAt"),
        "algorithm": doc.get("algorithm"),
    }
