"""Emit a scenario's events to stdout (JSONL) or an MQTT broker.

    python -m verge_sims.run --scenario vizag-like                 # JSONL to stdout
    python -m verge_sims.run --scenario vizag-like --mqtt localhost      # publish to MQTT
    python -m verge_sims.run --scenario vizag-like --redpanda localhost:19092
    python -m verge_sims.run --scenario vizag-like --realtime 10         # 10x speed

Readings publish to topic  verge/reading/{zoneId}/{sensorId}; permits and shift
events to  verge/{permit|shift}/{zoneId}. The edge gateway subscribes to these.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from .scenario import SCENARIOS


def _topic(e: dict) -> str:
    zone = e.get("zoneId", "unknown")
    if e["type"] == "reading":
        return f"verge/reading/{zone}/{e['sensorId']}"
    return f"verge/{e['type']}/{zone}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verge plant simulator")
    ap.add_argument("--scenario", default="vizag-like", choices=sorted(SCENARIOS))
    ap.add_argument("--mqtt", metavar="HOST", help="publish to this MQTT broker instead of stdout")
    ap.add_argument("--redpanda", metavar="BROKERS", help="publish canonical JSON to Redpanda")
    ap.add_argument("--topic", default="verge.events")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--realtime", type=float, default=0.0,
                    help="speed multiplier (0 = as fast as possible)")
    args = ap.parse_args(argv)

    events = list(SCENARIOS[args.scenario]().events())

    if args.redpanda:
        try:
            from confluent_kafka import Producer
        except ImportError as exc:
            print("verge_sims: confluent-kafka not installed", file=sys.stderr)
            raise SystemExit(1) from exc

        producer = Producer({"bootstrap.servers": args.redpanda})
        for e in events:
            producer.produce(args.topic, json.dumps(e).encode("utf-8"))
            producer.poll(0)
            if args.realtime:
                time.sleep(0.03 / args.realtime)
        producer.flush(10)
        print(
            f"published {len(events)} events to {args.topic} @ {args.redpanda}",
            file=sys.stderr,
        )
        return 0

    if args.mqtt:
        import paho.mqtt.client as mqtt  # lazy: only needed for live publish

        client = mqtt.Client()
        client.connect(args.mqtt, args.port, 60)
        client.loop_start()
        for e in events:
            client.publish(_topic(e), json.dumps(e))
            if args.realtime:
                time.sleep(0.03 / args.realtime)
        client.loop_stop()
        client.disconnect()
        print(f"published {len(events)} events to mqtt://{args.mqtt}:{args.port}", file=sys.stderr)
        return 0

    for e in events:
        sys.stdout.write(json.dumps(e) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
