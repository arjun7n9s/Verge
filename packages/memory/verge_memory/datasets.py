"""Dataset naming for per-site memory isolation."""

from __future__ import annotations

import os
import re

_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _clean(value: str) -> str:
    cleaned = _SAFE.sub("-", value.strip()).strip("-")
    return cleaned or "default"


def dataset_name(env: dict[str, str] | None = None) -> str:
    env = env or dict(os.environ)
    prefix = _clean(env.get("COGNEE_DATASET_PREFIX", "verge"))
    site = _clean(env.get("VERGE_SITE_ID", "default-site"))
    return f"{prefix}-{site}"
