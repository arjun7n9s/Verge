"""`verge` — the operator/engineer command line (spec §7).

    verge version
    verge replay --all | --incident vizag-2025-01
    verge rules list | validate
    verge sim --scenario vizag-like [--mqtt HOST]
"""

from __future__ import annotations

import argparse

from . import _paths  # noqa: F401  (sys.path bootstrap before verge imports)

__version__ = "0.3.0"


def _cmd_version(_args) -> int:
    print(f"verge {__version__}")
    return 0


def _cmd_replay(args) -> int:
    import sys as _sys

    from eval import harness

    argv = ["--incident", args.incident] if args.incident else ["--all"]
    saved = _sys.argv
    _sys.argv = ["harness", *argv]
    try:
        return harness.main()
    finally:
        _sys.argv = saved


def _cmd_rules(args) -> int:
    from verge_risk import STARTER_RULES, load_rules

    rules = load_rules(STARTER_RULES)
    if args.action == "list":
        for r in rules:
            fc = f" -> forecast {r.forecast.sensor_kind}" if r.forecast else ""
            print(f"{r.severity:8} {r.id:32} {r.name}{fc}")
        print(f"\n{len(rules)} rules in the starter library")
    elif args.action == "validate":
        bad = [r for r in rules if not r.predicates]
        if bad:
            print(f"INVALID: {len(bad)} rule(s) with no predicates")
            return 1
        print(f"OK: {len(rules)} rules valid")
    return 0


def _cmd_sim(args) -> int:
    from verge_sims.run import main as sim_main

    argv = ["--scenario", args.scenario]
    if args.mqtt:
        argv += ["--mqtt", args.mqtt]
    return sim_main(argv)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="verge", description="Verge command line")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version").set_defaults(func=_cmd_version)

    p_replay = sub.add_parser("replay", help="run the eval harness")
    p_replay.add_argument("--incident")
    p_replay.add_argument("--all", action="store_true")
    p_replay.set_defaults(func=_cmd_replay)

    p_rules = sub.add_parser("rules", help="inspect the Safety Rules DSL library")
    p_rules.add_argument("action", choices=["list", "validate"])
    p_rules.set_defaults(func=_cmd_rules)

    p_sim = sub.add_parser("sim", help="run a plant simulator")
    p_sim.add_argument("--scenario", default="vizag-like")
    p_sim.add_argument("--mqtt")
    p_sim.set_defaults(func=_cmd_sim)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
