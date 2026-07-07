"""In-process fan-out for SSE subscribers (spec §2 plane 5).

Push-on-change replaces the old 2s polling loop. An optional Redpanda
background consumer can also forward canonical events when
``VERGE_STREAM_FANOUT`` is enabled.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any


class StreamBus:
    """Thread-safe broadcaster for SSE clients."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[str]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        if q in self._queues:
            self._queues.remove(q)

    def _emit(self, payload: dict[str, Any]) -> None:
        if not self._loop or not self._queues:
            return
        line = f"data: {json.dumps(payload)}\n\n"

        def _put() -> None:
            for q in list(self._queues):
                with contextlib.suppress(asyncio.QueueFull):
                    q.put_nowait(line)

        self._loop.call_soon_threadsafe(_put)

    def publish_findings(self, findings: list[dict]) -> None:
        self._emit({"kind": "findings", "findings": findings})

    def publish_event(self, event: dict) -> None:
        self._emit({"kind": "event", "event": event})
