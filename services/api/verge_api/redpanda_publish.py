"""Optional Redpanda producer for outbox-drained canonical events."""

from __future__ import annotations

import json
import os

_producer = None
_failures = 0
_published = 0


def publish_enabled(env: dict[str, str] | None = None) -> bool:
    env = env or dict(os.environ)
    if env.get("VERGE_OUTBOX_REDPANDA", "true").lower() in {"0", "false", "no"}:
        return False
    return bool(env.get("REDPANDA_BROKERS"))


def maybe_publish_event(event: dict, *, env: dict[str, str] | None = None) -> bool:
    """Best-effort produce to ``VERGE_EVENTS_TOPIC``; never raises."""
    global _producer, _failures, _published
    env = env or dict(os.environ)
    if not publish_enabled(env):
        return False
    brokers = env["REDPANDA_BROKERS"]
    topic = env.get("VERGE_EVENTS_TOPIC", "verge.events")
    try:
        if _producer is None:
            from confluent_kafka import Producer

            _producer = Producer({"bootstrap.servers": brokers})
        _producer.produce(topic, json.dumps(event).encode())
        _producer.poll(0)
        _published += 1
        return True
    except Exception:
        _failures += 1
        return False


def publish_stats() -> dict:
    return {"published": _published, "failures": _failures}
