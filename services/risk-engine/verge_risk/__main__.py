"""`python -m verge_risk` — run the streaming engine over a canonical event stream.

    verge sim --scenario vizag-like | python -m verge_risk            # JSONL on stdin
    python -m verge_risk --source eval/replays/vizag-2025-01/events.jsonl
    ... --post http://localhost:8000     # also POST findings to the API (live console)
    ... --redpanda localhost:19092 --topic verge.events
"""

from __future__ import annotations

import argparse
import json
import sys

from . import STARTER_RULES, load_rules
from .runner import consume_redpanda, run_stream


def _events_from(path: str | None):
    stream = sys.stdin if path in (None, "-") else open(path, encoding="utf-8")  # noqa: SIM115
    with stream as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="verge_risk", description="Verge streaming risk engine")
    ap.add_argument("--source", help="JSONL file of canonical events (default: stdin)")
    ap.add_argument("--redpanda", help="brokers, e.g. localhost:19092 (overrides --source)")
    ap.add_argument("--topic", default="verge.events")
    ap.add_argument("--post", help="API base URL to POST findings to, e.g. http://localhost:8000")
    args = ap.parse_args(argv)

    rules = load_rules(STARTER_RULES)
    posted = {"n": 0}

    def sink(f):
        line = f.model_dump_json(by_alias=True)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        if args.post:
            import urllib.request

            req = urllib.request.Request(
                f"{args.post.rstrip('/')}/api/findings", data=line.encode(),
                headers={"Content-Type": "application/json"}, method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=5)  # noqa: S310
                posted["n"] += 1
            except Exception as exc:  # noqa: BLE001
                print(f"post failed: {exc}", file=sys.stderr)

    if args.redpanda:
        consume_redpanda(args.redpanda, args.topic, rules, sink)
    else:
        n = run_stream(_events_from(args.source), rules, sink)
        print(f"emitted {n} finding(s); posted {posted['n']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
