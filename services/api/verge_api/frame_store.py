"""Optional MinIO upload for vision frame JPEGs (Phase 2B lineage)."""

from __future__ import annotations

import io
import os
import uuid
from typing import Any


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


def upload_vision_frame(
    image: bytes,
    *,
    camera_id: str,
    content_type: str = "image/jpeg",
    env: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Upload a frame; return ``{uri, bucket, key}`` or None when MinIO unset/fails."""
    if not image:
        return None
    env = env or dict(os.environ)
    cfg = _settings(env)
    if cfg is None:
        return None
    try:
        from minio import Minio
    except ImportError:
        return None

    ext = "jpg"
    if "png" in (content_type or ""):
        ext = "png"
    key = f"vision/{camera_id}/{uuid.uuid4().hex}.{ext}"
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
            bucket,
            key,
            io.BytesIO(image),
            len(image),
            content_type=content_type or "image/jpeg",
        )
        return {
            "uploaded": True,
            "bucket": bucket,
            "key": key,
            "uri": f"s3://{bucket}/{key}",
        }
    except Exception:
        return None
