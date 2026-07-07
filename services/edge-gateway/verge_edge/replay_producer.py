"""Publish canonical JSONL events to Redpanda (spec §2 stream bus).

Bridges replay files and simulators into the same topic the risk-engine
consumes — completing sim → bus → engine → API in compose.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def publish_jsonl(
    path: str | Path,
    *,
    brokers: str,
    topic: str = "verge.events",
    realtime: float = 0.0,
) -> int:
    """Read a JSONL file and produce each line to ``topic``."""
    try:
        from confluent_kafka import Producer
    except ImportError:
        print("replay-producer: confluent-kafka not installed", file=sys.stderr)
        return 1

    p = Path(path)
    if not p.is_file():
        print(f"replay-producer: file not found: {p}", file=sys.stderr)
        return 1

    producer = Producer({"bootstrap.servers": brokers})
    count = 0
    prev_ts: str | None = None

    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if realtime and prev_ts and event.get("ts"):
                try:
                    from datetime import datetime

                    t0 = datetime.fromisoformat(prev_ts)
                    t1 = datetime.fromisoformat(event["ts"])
                    delay = (t1 - t0).total_seconds() / realtime
                    if delay > 0:
                        time.sleep(min(delay, 2.0))
                except ValueError:
                    pass
            producer.produce(topic, json.dumps(event).encode("utf-8"))
            producer.poll(0)
            prev_ts = event.get("ts")
            count += 1

    producer.flush(10)
    print(f"replay-producer: published {count} events to {topic} @ {brokers}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Publish JSONL canonical events to Redpanda")
    ap.add_argument("jsonl", help="path to events.jsonl")
    ap.add_argument("--brokers", default="localhost:19092")
    ap.add_argument("--topic", default="verge.events")
    ap.add_argument("--realtime", type=float, default=0.0,
                    help="speed multiplier for inter-event delay (0 = flood)")
    args = ap.parse_args(argv)
    return publish_jsonl(
        args.jsonl, brokers=args.brokers, topic=args.topic, realtime=args.realtime,
    )


if __name__ == "__main__":
    raise SystemExit(main())
