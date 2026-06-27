"""Protocol bridge: raw OPC-UA / MQTT payloads -> canonical Verge events.

The whole point of the edge plane is that everything downstream sees one shape
regardless of source protocol. Real OT data is filthy (missing fields, unit
mismatches, bad timestamps); the normalizer is where we reject or repair it, so
the rest of the system can assume clean canonical events.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


class NormalizationError(ValueError):
    """Raised on a payload that cannot be made into a canonical event."""


def _parse_ts(raw: str | float | int | None) -> str:
    if raw is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(raw, (int, float)):  # epoch seconds
        return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()
    # ISO string; normalize to tz-aware
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def normalize_mqtt(topic: str, payload: bytes | str) -> dict:
    """MQTT message -> canonical event.

    Topic convention: verge/{reading|permit|shift}/{zone}[/{sensor}].
    The body is JSON; the topic disambiguates and backfills routing fields.
    """
    parts = topic.strip("/").split("/")
    if len(parts) < 3 or parts[0] != "verge":
        raise NormalizationError(f"unrecognized topic: {topic!r}")
    kind = parts[1]
    body = json.loads(payload.decode() if isinstance(payload, bytes) else payload)

    if kind == "reading":
        for f in ("sensorId", "value"):
            if f not in body:
                raise NormalizationError(f"reading missing {f}")
        return {
            "type": "reading",
            "ts": _parse_ts(body.get("ts")),
            "sensorId": body["sensorId"],
            "kind": body.get("kind", "unknown"),
            "unit": body.get("unit", ""),
            "zoneId": body.get("zoneId", parts[2]),
            "value": float(body["value"]),
        }
    if kind in ("permit", "shift"):
        return {"type": kind, "ts": _parse_ts(body.get("ts")), **body}
    raise NormalizationError(f"unsupported event kind: {kind!r}")


def normalize_opcua(node_id: str, value: float, *, ts: str | float | None = None,
                    mapping: dict[str, dict]) -> dict:
    """OPC-UA node update -> canonical reading, using a node->sensor mapping table
    (commissioned per plant). Unmapped nodes are rejected, not guessed."""
    meta = mapping.get(node_id)
    if meta is None:
        raise NormalizationError(f"unmapped OPC-UA node: {node_id!r}")
    return {
        "type": "reading",
        "ts": _parse_ts(ts),
        "sensorId": meta["sensorId"],
        "kind": meta.get("kind", "unknown"),
        "unit": meta.get("unit", ""),
        "zoneId": meta["zoneId"],
        "value": float(value),
    }
