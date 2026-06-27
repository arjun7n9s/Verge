"""Safety Rules DSL (spec §6).

Declarative, hot-reloadable rules so plant safety engineers author compound-risk
combinations without writing code. A rule fires when ALL its predicates match
within a zone; each matched predicate contributes a signal (and thus lineage) to
the finding.

Example (YAML):

    - id: hot-work-elevated-gas
      name: Hot work near elevated/rising flammable gas
      severity: critical
      all:
        - type: permit_active
          kind: hot-work
        - type: gas_near_threshold
          sensor_kind: gas-lel
          pct: 0.10            # within 10% below the LEL alarm, OR rising
        - type: shift_changeover
      forecast:
        sensor_kind: gas-lel
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ForecastSpec:
    sensor_kind: str


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    severity: str  # info | warning | critical
    predicates: list[dict[str, Any]]
    forecast: ForecastSpec | None = None
    base_confidence: float = 0.7

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Rule:
        fc = d.get("forecast")
        return Rule(
            id=d["id"],
            name=d["name"],
            severity=d.get("severity", "warning"),
            predicates=list(d.get("all", [])),
            forecast=ForecastSpec(sensor_kind=fc["sensor_kind"]) if fc else None,
            base_confidence=float(d.get("base_confidence", 0.7)),
        )


def load_rules(path: str | Path) -> list[Rule]:
    """Load rules from a YAML file or a directory of *.yaml files."""
    p = Path(path)
    files = sorted(p.glob("*.yaml")) if p.is_dir() else [p]
    rules: list[Rule] = []
    for f in files:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        for raw in doc:
            rules.append(Rule.from_dict(raw))
    return rules


# Confidence weighting by severity (the ML layer will refine this later).
SEVERITY_CONFIDENCE: dict[str, float] = {"info": 0.4, "warning": 0.7, "critical": 0.85}
