"""SSE stream bus unit tests."""

from __future__ import annotations

import asyncio
import json

from verge_api.stream_bus import StreamBus


def test_stream_bus_publishes_findings():
    bus = StreamBus()
    loop = asyncio.new_event_loop()
    bus.bind_loop(loop)

    async def _run() -> None:
        q = await bus.subscribe()
        bus.publish_findings([{"findingId": "F-1"}])
        await asyncio.sleep(0.01)
        line = q.get_nowait()
        assert line.startswith("data: ")
        payload = json.loads(line.removeprefix("data: ").strip())
        assert payload["kind"] == "findings"
        assert payload["findings"][0]["findingId"] == "F-1"
        bus.unsubscribe(q)

    loop.run_until_complete(_run())
    loop.close()
