"""`python -m verge_risk` — run the streaming engine over a canonical event stream.

    verge sim --scenario vizag-like | python -m verge_risk            # JSONL on stdin
    python -m verge_risk --source eval/replays/vizag-2025-01/events.jsonl
    ... --post http://localhost:8000     # also POST findings to the API (live console)
    ... --shadow                          # shadow mode: tag findings, don't alert (§14.5)
    ... --plant services/twin/.../plant.yaml   # plant model for thresholds + adjacency
    ... --redpanda localhost:19092 --topic verge.events

The unified runtime: gas rules (risk-engine) + SIMOPS permit conflicts (permit),
resolved against the plant model (twin) for thresholds and zone adjacency.
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


def _simops_detector(adjacency):
    """Closure that runs SIMOPS conflict detection over the live permits. Imported
    here (not in runner) so risk-engine keeps no dependency on permit/twin."""
    from verge_permit import conflict_findings

    def detect(state):
        return conflict_findings(state.permits, adjacency=adjacency, now=state.now, at=state.now)

    return detect


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="verge_risk", description="Verge streaming risk engine")
    ap.add_argument("--source", help="JSONL file of canonical events (default: stdin)")
    ap.add_argument("--redpanda", help="brokers, e.g. localhost:19092 (overrides --source)")
    ap.add_argument("--topic", default="verge.events")
    ap.add_argument("--post", help="API base URL to POST findings to, e.g. http://localhost:8000")
    ap.add_argument("--plant", help="plant model YAML (default: the demo plant)")
    ap.add_argument("--no-simops", action="store_true", help="disable SIMOPS permit conflicts")
    ap.add_argument("--shadow", action="store_true", help="shadow mode: tag findings, don't alert")
    args = ap.parse_args(argv)

    rules = load_rules(STARTER_RULES)

    # Plant model -> thresholds + adjacency (twin). Defaults to the demo plant.
    from verge_twin import load_plant

    plant = load_plant(args.plant) if args.plant else load_plant()
    thresholds = plant.thresholds_by_kind()
    detectors = [] if args.no_simops else [_simops_detector(plant.adjacency())]

    posted = {"n": 0}
    permits_posted = {"n": 0}

    def _post_json(url: str, payload: str) -> None:
        import urllib.request

        req = urllib.request.Request(
            url,
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)  # noqa: S310

    def sink(f):
        line = f.model_dump_json(by_alias=True)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        if args.post:
            try:
                _post_json(f"{args.post.rstrip('/')}/api/findings", line)
                posted["n"] += 1
            except Exception as exc:  # noqa: BLE001
                print(f"post failed: {exc}", file=sys.stderr)

    def on_event(e: dict) -> None:
        if not args.post or e.get("type") != "permit":
            return
        body = json.dumps({
            "permitId": e["permitId"],
            "kind": e["kind"],
            "zoneId": e["zoneId"],
            "equipmentId": e.get("equipmentId"),
            "validFrom": e["validFrom"],
            "validTo": e["validTo"],
            "status": e.get("status", "open"),
        })
        try:
            _post_json(f"{args.post.rstrip('/')}/api/permits/upsert", body)
            permits_posted["n"] += 1
        except Exception as exc:  # noqa: BLE001
            print(f"permit post failed: {exc}", file=sys.stderr)

    stream_kw = {
        "thresholds": thresholds,
        "detectors": detectors,
        "shadow": args.shadow,
        "event_hook": on_event if args.post else None,
    }

    if args.redpanda:
        consume_redpanda(args.redpanda, args.topic, rules, sink, **stream_kw)
    else:
        n = run_stream(_events_from(args.source), rules, sink, **stream_kw)
        mode = "shadow" if args.shadow else "live"
        print(
            f"[{mode}] emitted {n} finding(s); posted {posted['n']}; "
            f"permits {permits_posted['n']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
