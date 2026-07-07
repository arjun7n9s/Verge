"""Parse canary rollout zone maps from environment (spec §14 P4)."""

from __future__ import annotations


def parse_canary_zones(raw: str) -> dict[str, set[str]]:
    """Parse ``model:zone1,zone2;other:Z-01`` into a router map."""
    out: dict[str, set[str]] = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        name, zones = part.split(":", 1)
        name = name.strip()
        if not name:
            continue
        out[name] = {z.strip() for z in zones.split(",") if z.strip()}
    return out
