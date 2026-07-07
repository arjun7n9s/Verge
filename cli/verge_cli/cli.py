"""`verge` — the operator/engineer command line (spec §7).

    verge version
    verge replay --all | --incident vizag-2025-01
    verge rules list | validate | adopt
    verge sim --scenario vizag-like [--mqtt HOST]

    # commissioning workflow (spec §14.5)
    verge plant import --file plant.geojson --name my-plant [--out plant.yaml]
    verge sensor map --csv sensors.csv --layout plant.geojson
    verge commission [--name my-plant --layout plant.geojson --sensors sensors.csv]
"""

from __future__ import annotations

import argparse
import json

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
    elif args.action == "adopt":
        # Commissioning step 3 (§14.5): adopt the starter library, per zone later.
        by_sev: dict[str, int] = {}
        for r in rules:
            by_sev[r.severity] = by_sev.get(r.severity, 0) + 1
        print(f"Adopted {len(rules)} rules from the {args.library} starter library.")
        for sev in ("critical", "warning", "info"):
            if sev in by_sev:
                print(f"  {sev:9} {by_sev[sev]}")
        print("\nCustomize per zone/shift before go-live; shadow mode validates them.")
    return 0


def _cmd_plant(args) -> int:
    """Commissioning step 1 (§14.5): import + validate a plant layout."""
    from verge_twin import (
        build_plant_model,
        load_zone_geometries,
        map_sensors,
        to_plant_yaml,
        validate_layout,
    )
    from verge_twin.commission import SensorMapping

    zones = load_zone_geometries(args.file)
    report = validate_layout(args.name, zones)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Plant '{args.name}': {len(zones)} zones, "
              f"{'clean' if report.ok else 'ISSUES'}")
        for a, b in report.overlaps:
            print(f"  OVERLAP  {a} ∩ {b}")
        for z in report.invalid_zones:
            print(f"  INVALID  {z} (degenerate polygon)")
        for zid in report.zones:
            if zid in report.invalid_zones:
                continue
            adj = ", ".join(report.adjacency.get(zid, [])) or "(isolated)"
            print(f"  {zid:8} adjacent: {adj}")
        print(f"  coverage: {report.coverage_ratio:.0%} of footprint")
    if args.out:
        mapping = (map_sensors(args.sensors, zones) if args.sensors
                   else SensorMapping(plant=args.name))
        model = build_plant_model(args.name, report, zones, mapping)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(to_plant_yaml(model))
        print(f"  wrote {args.out}")
    return 0 if report.ok else 1


def _cmd_sensor(args) -> int:
    """Commissioning step 2 (§14.5): map sensors to zones."""
    from verge_twin import load_zone_geometries, map_sensors

    zones = load_zone_geometries(args.layout)
    mapping = map_sensors(args.csv, zones)
    if args.json:
        print(json.dumps(mapping.to_dict(), indent=2))
    else:
        for s in mapping.mapped:
            print(f"  {s.sensor_id:10} -> {s.zone_id}")
        for sid in sorted(mapping.unassigned):
            print(f"  {sid:10} -> UNASSIGNED (excluded from scoring)")
        print(f"\n{len(mapping.mapped)} mapped, {len(mapping.unassigned)} unassigned")
    return 0 if not mapping.unassigned else 1


def _cmd_validate(args) -> int:
    """Validate a canonical-event JSONL stream against the data contracts (§14 P4).

        verge ingest --demo historian | verge validate
    """
    import sys
    from pathlib import Path

    from verge_contracts import validate_stream

    if args.file:
        lines = Path(args.file).read_text(encoding="utf-8").splitlines()
    else:
        lines = sys.stdin.read().splitlines()
    events = [json.loads(ln) for ln in lines if ln.strip()]
    report = validate_stream(events)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for v in report["violations"]:
            print(f"  INVALID {v['eventType']}: {'; '.join(v['errors'])}")
        print(f"\n{report['valid']}/{report['total']} events conform "
              f"({report['invalid']} invalid)")
    return 0 if report["invalid"] == 0 else 1


def _cmd_models(args) -> int:
    """List the model registry (MLOps lifecycle, §14 Phase 4)."""
    import os

    from verge_mlops import DEMO_REGISTRY, ModelRegistry

    path = args.registry or os.environ.get("VERGE_MODEL_REGISTRY")
    reg = ModelRegistry(path) if path else ModelRegistry.read_only(DEMO_REGISTRY)
    if args.json:
        print(json.dumps({"summary": reg.summary(),
                          "models": [c.to_dict() for c in reg.list()]}, indent=2))
    else:
        for c in reg.list():
            print(f"  {c.stage:11} {c.name:16} {c.version:12} {c.kind}")
        summary = reg.summary()
        prod = ", ".join(f"{n}={v}" for n, v in summary["production"].items()) or "(none)"
        print(f"\n{summary['total']} models · production: {prod}")
    return 0


def _cmd_ingest(args) -> int:
    """Pull canonical events from an integration-hub connector (spec §14).

    Emits one canonical event per line on stdout — pipeable straight into the
    risk engine, the same shape as `verge sim`:

        verge ingest --connector csv-historian ... | python -m verge_risk
    """
    import sys

    from verge_connectors import CONNECTOR_NAMES, demo_cmms, demo_historian, get_connector

    if args.demo == "historian":
        conn = demo_historian()
    elif args.demo == "cmms":
        conn = demo_cmms()
    else:
        conn = get_connector(args.connector)

    result = conn.pull(since=args.since)
    for event in result.events:
        print(json.dumps(event))
    status = "degraded" if result.degraded else "ok"
    msg = f"[ingest] {conn.name}: {len(result.events)} events, {result.skipped} skipped ({status})"
    if result.degraded and result.reason:
        msg += f" — {result.reason}"
    print(msg, file=sys.stderr)
    if args.connector and args.connector not in CONNECTOR_NAMES and not args.demo:
        print(f"[ingest] unknown connector '{args.connector}'; known: "
              f"{', '.join(CONNECTOR_NAMES)}", file=sys.stderr)
    return 0 if not result.degraded else 1


def _cmd_compliance(args) -> int:
    """OISD/Factory Act/DGMS gap assessment for a commissioned plant (§5)."""
    from datetime import UTC, datetime

    from verge_compliance import assess, build_compliance_pack, render_markdown
    from verge_risk import STARTER_RULES, load_rules
    from verge_twin import load_plant

    plant = load_plant(args.plant) if args.plant else load_plant()
    rules = load_rules(args.rules or STARTER_RULES)
    report = assess(plant, rules)
    pack = build_compliance_pack(report, created_at=datetime.now(UTC))
    if args.json:
        print(json.dumps({**report.to_dict(), "evidencePack": pack.to_dict()},
                         indent=2, default=str))
    else:
        md = render_markdown(report, pack)
        print(md)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(md + "\n")
    # Gaps are reported, not fatal — a plant closes them during commissioning.
    return 0


def _cmd_backup(args) -> int:
    """Create or verify an audit-chain snapshot via the API (§14.6)."""
    import urllib.request
    from pathlib import Path

    base = args.api.rstrip("/")
    try:
        if args.backup_cmd == "create":
            with urllib.request.urlopen(f"{base}/api/ops/backup", timeout=10) as r:  # noqa: S310
                snap = r.read().decode()
            if args.out:
                Path(args.out).write_text(snap, encoding="utf-8")
                print(f"[backup] wrote {args.out}")
            else:
                print(snap)
            return 0
        # verify
        data = Path(args.file).read_bytes()
        req = urllib.request.Request(  # noqa: S310
            f"{base}/api/ops/backup/verify", data=data,
            headers={"content-type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            report = json.loads(r.read().decode())
    except OSError as e:
        print(f"[backup] could not reach API at {args.api}: {e}")
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report.get("verified") else 1


def _cmd_incident_report(args) -> int:
    """Generate a hash-chained incident report for a finding via the API (§14 P3)."""
    import urllib.request

    url = f"{args.api.rstrip('/')}/api/findings/{args.finding}/incident-report"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 (operator-supplied)
            body = json.loads(resp.read().decode())
    except OSError as e:
        print(f"[incident-report] could not reach API at {args.api}: {e}")
        return 1
    if args.json:
        print(json.dumps(body, indent=2))
    else:
        print(body.get("markdown", ""))
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(body.get("markdown", "") + "\n")
    return 0


def _cmd_commission(args) -> int:
    """The full 6-step commissioning workflow (§14.5)."""
    from .commission import DEMO_LAYOUT, DEMO_SENSORS, render_markdown, run_commission

    layout = args.layout or DEMO_LAYOUT
    sensors = args.sensors if args.layout else (args.sensors or DEMO_SENSORS)
    replays = [args.replay] if args.replay else None
    report = run_commission(args.name, layout, sensors, args.rules, replays)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        md = render_markdown(report)
        print(md)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(md + "\n")
    return 0 if report.ready else 1


def _cmd_sim(args) -> int:
    from verge_sims.run import main as sim_main

    argv = ["--scenario", args.scenario]
    if args.mqtt:
        argv += ["--mqtt", args.mqtt]
    if args.redpanda:
        argv += ["--redpanda", args.redpanda, "--topic", args.topic]
    if args.realtime:
        argv += ["--realtime", str(args.realtime)]
    return sim_main(argv)


def _cmd_publish(args) -> int:
    from verge_edge.replay_producer import publish_jsonl

    return publish_jsonl(
        args.file,
        brokers=args.brokers,
        topic=args.topic,
        realtime=args.realtime,
    )


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="verge", description="Verge command line")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version").set_defaults(func=_cmd_version)

    p_replay = sub.add_parser("replay", help="run the eval harness")
    grp = p_replay.add_mutually_exclusive_group()  # --incident and --all are exclusive
    grp.add_argument("--incident")
    grp.add_argument("--all", action="store_true")
    p_replay.set_defaults(func=_cmd_replay)

    p_rules = sub.add_parser("rules", help="inspect / adopt the Safety Rules DSL library")
    p_rules.add_argument("action", choices=["list", "validate", "adopt"])
    p_rules.add_argument("--library", default="oisd-starter",
                         help="starter library name (commissioning step 3)")
    p_rules.set_defaults(func=_cmd_rules)

    p_sim = sub.add_parser("sim", help="run a plant simulator")
    p_sim.add_argument("--scenario", default="vizag-like")
    p_sim.add_argument("--mqtt")
    p_sim.add_argument("--redpanda", metavar="BROKERS", help="publish to Redpanda")
    p_sim.add_argument("--topic", default="verge.events")
    p_sim.add_argument("--realtime", type=float, default=0.0)
    p_sim.set_defaults(func=_cmd_sim)

    p_pub = sub.add_parser("publish", help="publish a JSONL replay file to Redpanda")
    p_pub.add_argument("file", help="canonical events JSONL")
    p_pub.add_argument("--brokers", default="localhost:19092")
    p_pub.add_argument("--topic", default="verge.events")
    p_pub.add_argument("--realtime", type=float, default=0.0)
    p_pub.set_defaults(func=_cmd_publish)

    # --- commissioning workflow (spec §14.5) ---
    p_plant = sub.add_parser("plant", help="commission a plant layout")
    plant_sub = p_plant.add_subparsers(dest="plant_cmd", required=True)
    p_import = plant_sub.add_parser("import", help="import + validate a plant layout (step 1)")
    p_import.add_argument("--file", required=True, help="zone GeoJSON")
    p_import.add_argument("--name", required=True)
    p_import.add_argument("--sensors", help="optional sensor CSV to embed")
    p_import.add_argument("--out", help="write the commissioned plant YAML here")
    p_import.add_argument("--json", action="store_true")
    p_import.set_defaults(func=_cmd_plant)

    p_sensor = sub.add_parser("sensor", help="map sensors to zones")
    sensor_sub = p_sensor.add_subparsers(dest="sensor_cmd", required=True)
    p_map = sensor_sub.add_parser("map", help="map sensors to zones (step 2)")
    p_map.add_argument("--csv", required=True)
    p_map.add_argument("--layout", required=True, help="zone GeoJSON")
    p_map.add_argument("--json", action="store_true")
    p_map.set_defaults(func=_cmd_sensor)

    p_validate = sub.add_parser("validate", help="validate a canonical-event JSONL stream (§14 P4)")
    p_validate.add_argument("--file", help="JSONL file (default: stdin)")
    p_validate.add_argument("--json", action="store_true")
    p_validate.set_defaults(func=_cmd_validate)

    p_models = sub.add_parser("models", help="list the model registry (§14 Phase 4)")
    p_models.add_argument("--registry", help="registry JSON path (default: bundled demo)")
    p_models.add_argument("--json", action="store_true")
    p_models.set_defaults(func=_cmd_models)

    p_ingest = sub.add_parser("ingest", help="pull canonical events from a connector (§14)")
    p_ingest.add_argument("--connector", default="",
                          help="csv-historian | csv-cmms | pi | phd | maximo | sap-pm | milestone")
    p_ingest.add_argument("--demo", choices=["historian", "cmms"],
                          help="use the bundled demo source (no env needed)")
    p_ingest.add_argument("--since", help="only events at/after this ISO timestamp")
    p_ingest.set_defaults(func=_cmd_ingest)

    p_compliance = sub.add_parser("compliance", help="OISD/Factory Act gap assessment (§5)")
    p_compliance.add_argument("--plant", help="plant YAML (default: Vizag demo)")
    p_compliance.add_argument("--rules", help="rules file/dir (default: starter library)")
    p_compliance.add_argument("--out", help="write the markdown report here")
    p_compliance.add_argument("--json", action="store_true")
    p_compliance.set_defaults(func=_cmd_compliance)

    p_backup = sub.add_parser("backup", help="create/verify an audit-chain snapshot (§14.6)")
    backup_sub = p_backup.add_subparsers(dest="backup_cmd", required=True)
    p_bc = backup_sub.add_parser("create", help="export the audit chain snapshot")
    p_bc.add_argument("--api", default="http://localhost:8000")
    p_bc.add_argument("--out", help="write the snapshot JSON here")
    p_bc.set_defaults(func=_cmd_backup)
    p_bv = backup_sub.add_parser("verify", help="replay + verify a snapshot")
    p_bv.add_argument("--file", required=True, help="snapshot JSON")
    p_bv.add_argument("--api", default="http://localhost:8000")
    p_bv.set_defaults(func=_cmd_backup)

    p_ir = sub.add_parser("incident-report", help="hash-chained incident report (§14 P3)")
    p_ir.add_argument("--finding", required=True, help="finding id")
    p_ir.add_argument("--api", default="http://localhost:8000", help="API base URL")
    p_ir.add_argument("--out", help="write the markdown report here")
    p_ir.add_argument("--json", action="store_true")
    p_ir.set_defaults(func=_cmd_incident_report)

    p_comm = sub.add_parser("commission", help="run the full 6-step workflow (§14.5)")
    p_comm.add_argument("--name", default="vizag-coke-oven")
    p_comm.add_argument("--layout", help="zone GeoJSON (default: Vizag demo)")
    p_comm.add_argument("--sensors", help="sensor CSV (default: Vizag demo)")
    p_comm.add_argument("--rules", help="rules file/dir (default: starter library)")
    p_comm.add_argument("--replay", help="single incident id (default: all replays)")
    p_comm.add_argument("--out", help="write the markdown report here")
    p_comm.add_argument("--json", action="store_true")
    p_comm.set_defaults(func=_cmd_commission)

    return ap


def _force_utf8_stdout() -> None:
    """The commissioning report uses Unicode (✅ ⚠️ ∩ ·); the Windows console
    defaults to cp1252. Reconfigure to UTF-8 so output never crashes on encoding."""
    import contextlib
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
