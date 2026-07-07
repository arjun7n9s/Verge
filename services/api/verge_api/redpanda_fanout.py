"""Optional Redpanda → SSE bridge for live canonical events."""

from __future__ import annotations

import json
import os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stream_bus import StreamBus


def fanout_enabled(env: dict[str, str] | None = None) -> bool:
    env = env or dict(os.environ)
    return env.get("VERGE_STREAM_FANOUT", "").lower() in ("1", "true", "yes")


def start_redpanda_fanout(
    bus: StreamBus,
    *,
    env: dict[str, str] | None = None,
) -> threading.Event | None:
    """Background thread: consume ``VERGE_EVENTS_TOPIC`` and push to SSE bus."""
    env = env or dict(os.environ)
    if not fanout_enabled(env):
        return None
    brokers = env.get("REDPANDA_BROKERS")
    topic = env.get("VERGE_EVENTS_TOPIC", "verge.events")
    if not brokers:
        return None

    stop = threading.Event()

    def _run() -> None:
        try:
            from confluent_kafka import Consumer
        except ImportError:
            return
        consumer = Consumer({
            "bootstrap.servers": brokers,
            "group.id": env.get("VERGE_STREAM_GROUP", "verge-api-sse"),
            "auto.offset.reset": "latest",
        })
        consumer.subscribe([topic])
        try:
            while not stop.is_set():
                msg = consumer.poll(0.5)
                if msg is None or msg.error():
                    continue
                try:
                    event = json.loads(msg.value())
                except (json.JSONDecodeError, TypeError):
                    continue
                bus.publish_event(event)
        finally:
            consumer.close()

    threading.Thread(target=_run, name="verge-redpanda-fanout", daemon=True).start()
    return stop
