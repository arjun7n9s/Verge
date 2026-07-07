"""Forward canonical events to the Verge API (optional live path beside Redpanda)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from verge_contracts.trace import TRACE_HEADER


def forward_to_api(base_url: str, event: dict, *, timeout: float = 5.0) -> None:
    """POST readings and permits to the API gateway; ignore unsupported kinds."""
    base = base_url.rstrip("/")
    if event.get("type") == "reading":
        url = f"{base}/api/readings/ingest"
        body = {
            "ts": event["ts"],
            "sensorId": event["sensorId"],
            "kind": event.get("kind", "unknown"),
            "unit": event.get("unit", ""),
            "zoneId": event.get("zoneId", ""),
            "value": float(event["value"]),
        }
    elif event.get("type") == "permit":
        url = f"{base}/api/permits/upsert"
        body = {
            "permitId": event["permitId"],
            "kind": event["kind"],
            "zoneId": event["zoneId"],
            "equipmentId": event.get("equipmentId"),
            "validFrom": event["validFrom"],
            "validTo": event["validTo"],
            "status": event.get("status", "open"),
        }
    else:
        return

    headers = {"Content-Type": "application/json"}
    trace_id = event.get("traceId")
    if trace_id:
        headers[TRACE_HEADER] = str(trace_id)

    req = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API forward failed: {exc}") from exc
