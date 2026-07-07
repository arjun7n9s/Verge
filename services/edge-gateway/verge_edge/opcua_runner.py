"""OPC-UA ingest runner (spec §2 plane 1).

Polls mapped OPC-UA nodes and emits canonical reading events. Degrades when
``asyncua`` is not installed or ``VERGE_OPCUA_ENDPOINT`` is unset — the edge
gateway never fabricates readings (P4).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .normalize import normalize_opcua


def _emit(event: dict) -> None:
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def run_opcua(
    *,
    endpoint: str,
    node_map: dict[str, str],
    poll_s: float = 2.0,
    once: bool = False,
) -> int:
    """Poll OPC-UA nodes. ``node_map`` maps node_id -> sensor_id."""
    try:
        import asyncio

        from asyncua import Client  # type: ignore[import-untyped]
    except ImportError:
        print("opcua: asyncua not installed — degraded (no readings emitted)", file=sys.stderr)
        return 0

    async def _poll() -> None:
        mapping = {
            node_id: {"sensorId": sensor_id, "zoneId": "unknown", "kind": "unknown", "unit": ""}
            for node_id, sensor_id in node_map.items()
        }
        async with Client(url=endpoint) as client:
            while True:
                for node_id in node_map:
                    try:
                        node = client.get_node(node_id)
                        value = await node.read_value()
                        _emit(normalize_opcua(node_id, float(value), mapping=mapping))
                    except Exception as exc:  # noqa: BLE001
                        print(f"opcua read failed {node_id}: {exc}", file=sys.stderr)
                if once:
                    break
                await asyncio.sleep(poll_s)

    asyncio.run(_poll())
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="verge_edge.opcua", description="OPC-UA → canonical events")
    ap.add_argument("--endpoint", default=os.environ.get("VERGE_OPCUA_ENDPOINT"))
    ap.add_argument("--map", help="JSON object nodeId -> sensorId")
    ap.add_argument("--poll", type=float, default=2.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)

    if not args.endpoint:
        print("opcua: VERGE_OPCUA_ENDPOINT unset — degraded", file=sys.stderr)
        return 0

    node_map = json.loads(args.map) if args.map else {}
    if not node_map:
        print("opcua: empty node map — nothing to poll", file=sys.stderr)
        return 0

    return run_opcua(endpoint=args.endpoint, node_map=node_map, poll_s=args.poll, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
