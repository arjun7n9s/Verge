"""Gap detection: does a commissioned plant satisfy each regulatory clause?

The detector is deterministic and LLM-free (a compliance gap is a legal claim;
it must be reproducible, not generated). For each clause we ask whether the
plant demonstrates the required capability:

* **platform** capabilities are satisfied by the Verge core.
* **config** capabilities are proven by the plant's own sensors + adopted rules;
  a config capability the plant has not configured is an honest gap and is
  reported as such — Verge does not paper over a plant's missing controls.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from verge_risk.rules import Rule
from verge_twin.plant import PlantModel

from .clauses import Clause, load_clauses

STATUS_SATISFIED = "satisfied"
STATUS_GAP = "gap"


def _predicate_matches(rules: list[Rule], type_: str, **match: Any) -> bool:
    for r in rules:
        for p in r.predicates:
            if p.get("type") != type_:
                continue
            if all(p.get(k) == v for k, v in match.items()):
                return True
    return False


def _rule_text_mentions(rules: list[Rule], *needles: str) -> bool:
    for r in rules:
        blob = f"{r.id} {r.name}".lower()
        if any(n in blob for n in needles):
            return True
    return False


def _gas_sensors(plant: PlantModel):
    # "gas-" prefix (gas-lel, gas-co, gas-h2s, …) — not a bare "gas" substring,
    # so an unrelated kind like "gasoline-level" is not miscounted as detection.
    return [s for s in plant.sensors.values() if s.kind.startswith("gas-")]


def _has_adjacency(plant: PlantModel) -> bool:
    return any(neighbours for neighbours in plant.adjacency().values())


# capability -> detector(plant, rules) -> satisfied?  (config capabilities only)
CONFIG_DETECTORS: dict[str, Callable[[PlantModel, list[Rule]], bool]] = {
    "gas-detection": lambda plant, rules: bool(_gas_sensors(plant)),
    "hot-work-control": lambda plant, rules: _predicate_matches(
        rules, "permit_active", kind="hot-work"
    ),
    "confined-space-control": lambda plant, rules: _predicate_matches(
        rules, "permit_active", kind="confined-space"
    ),
    "simops-review": lambda plant, rules: _has_adjacency(plant),
    "adjacency": lambda plant, rules: _has_adjacency(plant),
    "shift-handover": lambda plant, rules: _predicate_matches(rules, "shift_changeover"),
    "gas-drift-monitoring": lambda plant, rules: (
        _predicate_matches(rules, "gas_near_threshold")
        and len({s.zone_id for s in _gas_sensors(plant)}) >= 2
    ),
    "isolation-control": lambda plant, rules: (
        _predicate_matches(rules, "permit_active", kind="isolation")
        or _rule_text_mentions(rules, "isolation", "lockout")
    ),
    "startup-monitoring": lambda plant, rules: _rule_text_mentions(
        rules, "startup", "start-up", "abnormal"
    ),
    "tank-farm-monitoring": lambda plant, rules: (
        any(e.kind == "tank" for e in plant.equipment.values())
        or _rule_text_mentions(rules, "tank", "overflow", "vapor", "vapour")
    ),
}


@dataclass
class ClauseResult:
    clause: Clause
    status: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "clauseId": self.clause.id,
            "oisdRef": self.clause.oisd_ref,
            "standard": self.clause.standard,
            "title": self.clause.title,
            "requirement": self.clause.requirement,
            "capability": self.clause.capability,
            "isPlatform": self.clause.is_platform,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass
class ComplianceReport:
    plant: str
    results: list[ClauseResult] = field(default_factory=list)

    @property
    def satisfied(self) -> int:
        return sum(1 for r in self.results if r.status == STATUS_SATISFIED)

    @property
    def gaps(self) -> list[ClauseResult]:
        return [r for r in self.results if r.status == STATUS_GAP]

    @property
    def coverage_ratio(self) -> float:
        return self.satisfied / len(self.results) if self.results else 0.0

    def to_dict(self) -> dict:
        return {
            "plant": self.plant,
            "coverageRatio": round(self.coverage_ratio, 4),
            "satisfied": self.satisfied,
            "gaps": len(self.gaps),
            "total": len(self.results),
            "clauses": [r.to_dict() for r in self.results],
        }


def assess(
    plant: PlantModel, rules: list[Rule], clauses: list[Clause] | None = None
) -> ComplianceReport:
    """Assess a commissioned plant + adopted rules against the clause library."""
    clauses = clauses or load_clauses()
    report = ComplianceReport(plant=plant.name)
    for clause in clauses:
        if clause.is_platform:
            report.results.append(
                ClauseResult(clause, STATUS_SATISFIED, "provided by the Verge core")
            )
            continue
        detector = CONFIG_DETECTORS.get(clause.capability)
        if detector is None:
            report.results.append(
                ClauseResult(clause, STATUS_GAP, f"no detector for '{clause.capability}'")
            )
        elif detector(plant, rules):
            report.results.append(
                ClauseResult(
                    clause, STATUS_SATISFIED,
                    f"plant demonstrates '{clause.capability}'"
                )
            )
        else:
            report.results.append(
                ClauseResult(
                    clause, STATUS_GAP,
                    f"no sensor/rule demonstrates '{clause.capability}'"
                )
            )
    return report


def gap_findings(report: ComplianceReport) -> list[dict]:
    """Express each gap as a regulatory-gap payload (hash-chainable via audit)."""
    return [
        {
            "kind": "regulatory-gap",
            "plant": report.plant,
            "clauseId": r.clause.id,
            "oisdRef": r.clause.oisd_ref,
            "standard": r.clause.standard,
            "requirement": r.clause.requirement,
            "capability": r.clause.capability,
        }
        for r in report.gaps
    ]
