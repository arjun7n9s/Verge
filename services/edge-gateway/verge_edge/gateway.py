"""Runner: subscribe to MQTT, normalize, produce to Redpanda. Thin by design —
the logic worth testing lives in normalize.py and buffer.py.

    python -m verge_edge.gateway --mqtt localhost --brokers localhost:19092
"""

from __future__ import annotations

import argparse
import json
import sys

from .buffer import StoreAndForward
from .normalize import NormalizationError, normalize_mqtt

CANONICAL_TOPIC = "verge.events"


def _make_producer(brokers: str):
    from confluent_kafka import Producer  # lazy

    return Producer({"bootstrap.servers": brokers})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verge edge gateway")
    ap.add_argument("--mqtt", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--brokers", default="localhost:19092")
    args = ap.parse_args(argv)

    import paho.mqtt.client as mqtt  # lazy

    producer = _make_producer(args.brokers)
    saf = StoreAndForward()

    def to_bus(event: dict) -> None:
        producer.produce(CANONICAL_TOPIC, json.dumps(event).encode())
        producer.poll(0)

    def on_message(_client, _userdata, msg) -> None:
        try:
            event = normalize_mqtt(msg.topic, msg.payload)
        except NormalizationError as e:
            print(f"drop: {e}", file=sys.stderr)
            return
        saf.submit(event, to_bus)

    client = mqtt.Client()
    client.on_message = on_message
    client.connect(args.mqtt, args.port, 60)
    client.subscribe("verge/#")
    print(f"edge-gateway: mqtt://{args.mqtt}:{args.port} -> {args.brokers}/{CANONICAL_TOPIC}",
          file=sys.stderr)
    client.loop_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
