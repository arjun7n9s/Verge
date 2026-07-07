"""Commissioning workflow report (spec §14.5).

Shared by the CLI and API so both surfaces run the same readiness logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from verge_risk import STARTER_RULES, load_rules
from verge_twin import (
    build_plant_model,
    load_zone_geometries,
    map_sensors,
    validate_layout,
)
from verge_twin.commission import SensorMapping
from verge_twin.plant import PLANTS_DIR

DEMO_LAYOUT = PLANTS_DIR / "vizag-zones.geojson"
DEMO_SENSORS = PLANTS_DIR / "vizag-sensors.csv"
MIN_RULES_FOR_GOLIVE = 30


@dataclass
class Check:
    step: str
    status: str
    detail: str


@dataclass
class CommissioningReport:
    plant: str
    checks: list[Check] = field(default_factory=list)
    layout: dict = field(default_factory=dict)
    sensors: dict = field(default_factory=dict)
    rules: dict = field(default_factory=dict)
    dry_run: list[dict] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    def to_dict(self) -> dict:
        return {
            "plant": self.plant,
            "ready": self.ready,
            "checks": [
                {"step": c.step, "status": c.status, "detail": c.detail} for c in self.checks
            ],
            "layout": self.layout,
            "sensors": self.sensors,
            "rules": self.rules,
            "dryRun": self.dry_run,
        }


def _dry_run(replays: list[str]) -> list[dict]:
    from eval.harness import run_incident

    return [run_incident(i) for i in replays]


def _available_replays() -> list[str]:
    from eval.runtime import REPLAYS

    return sorted(p.name for p in REPLAYS.iterdir() if (p / "ground-truth.json").exists())


def run_commission(
    name: str,
    layout_path: str | Path,
    sensors_path: str | Path | None,
    rules_path: str | Path | None = None,
    replays: list[str] | None = None,
) -> CommissioningReport:
    report = CommissioningReport(plant=name)
    zones = load_zone_geometries(layout_path)
    layout = validate_layout(name, zones)
    report.layout = layout.to_dict()
    if not zones:
        report.checks.append(Check("1 · layout", "fail", "no zones found in layout"))
    elif layout.overlaps:
        pairs = ", ".join(f"{a}∩{b}" for a, b in layout.overlaps)
        report.checks.append(Check("1 · layout", "fail", f"overlapping zones: {pairs}"))
    elif layout.isolated_zones:
        report.checks.append(Check(
            "1 · layout", "warn",
            f"{len(zones)} zones, isolated (no neighbour): {', '.join(layout.isolated_zones)}"))
    else:
        report.checks.append(Check(
            "1 · layout", "pass",
            f"{len(zones)} zones, {len(layout.overlaps)} overlaps, adjacency inferred"))

    mapping = map_sensors(sensors_path, zones) if sensors_path else SensorMapping(plant=name)
    report.sensors = mapping.to_dict()
    if not mapping.mapped and not mapping.unassigned:
        report.checks.append(Check("2 · sensors", "warn", "no sensor CSV provided"))
    elif mapping.unassigned:
        report.checks.append(Check(
            "2 · sensors", "warn",
            f"{len(mapping.mapped)} mapped, {len(mapping.unassigned)} unassigned "
            f"(excluded from scoring): {', '.join(sorted(mapping.unassigned))}"))
    else:
        report.checks.append(Check(
            "2 · sensors", "pass", f"{len(mapping.mapped)} sensors mapped to zones"))

    rules = load_rules(rules_path or STARTER_RULES)
    by_sev: dict[str, int] = {}
    for r in rules:
        by_sev[r.severity] = by_sev.get(r.severity, 0) + 1
    report.rules = {
        "count": len(rules),
        "bySeverity": by_sev,
        "library": str(rules_path or "starter"),
    }
    if len(rules) < MIN_RULES_FOR_GOLIVE:
        report.checks.append(Check(
            "3 · rules", "warn", f"{len(rules)} rules adopted (target 30+ for go-live)"))
    else:
        report.checks.append(Check("3 · rules", "pass", f"{len(rules)} rules adopted ({by_sev})"))

    model = build_plant_model(name, layout, zones, mapping)
    kinds = {s.kind for s in model.sensors.values()}
    with_threshold = {s.kind for s in model.sensors.values() if s.threshold is not None}
    missing = sorted(kinds - with_threshold)
    if not kinds:
        report.checks.append(Check("4 · thresholds", "warn", "no mapped sensors to threshold"))
    elif missing:
        report.checks.append(Check(
            "4 · thresholds", "warn", f"sensor kinds without a threshold: {missing}"))
    else:
        report.checks.append(Check("4 · thresholds", "pass", f"thresholds set for {sorted(kinds)}"))

    replays = replays or _available_replays()
    report.dry_run = _dry_run(replays)
    caught = [d for d in report.dry_run if d["verge"]["alertTs"]]
    if not report.dry_run:
        report.checks.append(Check("5 · dry-run", "warn", "no historical replays available"))
    elif not caught:
        report.checks.append(Check(
            "5 · dry-run", "fail",
            "Verge was silent on every replay — tune rules/thresholds"))
    else:
        calibrated = sum(1 for d in caught if d["verge"].get("bandCalibrated"))
        report.checks.append(Check(
            "5 · dry-run", "pass",
            f"caught {len(caught)}/{len(report.dry_run)} incidents, "
            f"{calibrated} with a calibrated lead-time band"))

    report.checks.append(Check(
        "6 · shadow", "pass" if report.ready else "warn",
        "30-day default-on shadow mode is the next step — no plant goes live "
        "without it" if report.ready else "resolve the items above, then start shadow mode"))

    return report
