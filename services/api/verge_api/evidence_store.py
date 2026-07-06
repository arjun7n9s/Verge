"""Optional MinIO upload for evidence manifests (Dex D7).

Skips silently when MINIO_* is not configured or upload fails.
"""

from __future__ import annotations

import io
import json
import os
from typing import Any

from verge_schema.audit import EvidencePack


def _settings(env: dict[str, str]) -> dict[str, str | bool] | None:
    endpoint = env.get("MINIO_ENDPOINT")
    access = env.get("MINIO_ACCESS_KEY")
    secret = env.get("MINIO_SECRET_KEY")
    if not endpoint or not access or not secret:
        return None
    return {
        "endpoint": endpoint.replace("http://", "").replace("https://", ""),
        "access": access,
        "secret": secret,
        "bucket": env.get("MINIO_BUCKET_EVIDENCE", "verge-evidence"),
        "secure": env.get("MINIO_USE_SSL", "false").lower() in {"1", "true", "yes"},
    }


def upload_evidence_manifest(
    pack: EvidencePack,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Upload manifest JSON to MinIO when configured; return metadata or None."""
    env = env or dict(os.environ)
    cfg = _settings(env)
    if cfg is None:
        return None

    try:
        from minio import Minio
    except ImportError:
        return None

    manifest = {
        "packId": pack.pack_id,
        "findingId": pack.finding_id,
        "items": pack.items,
        "manifestHash": pack.manifest_hash,
        "createdAt": pack.created_at.isoformat(),
    }
    body = json.dumps(manifest, indent=2).encode("utf-8")
    key = f"{pack.finding_id}/{pack.pack_id}.json"

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
        client.put_object(bucket, key, io.BytesIO(body), len(body), content_type="application/json")
        return {"bucket": bucket, "key": key, "uploaded": True}
    except Exception:
        return None
