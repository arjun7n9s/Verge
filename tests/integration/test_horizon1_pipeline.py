"""Capstone: the Horizon-1 surfaces work as one pipeline.

connector ingest → data-contract validation → compound risk engine (+SIMOPS)
→ hash-chained incident report → compliance assessment.

This is the cross-module regression net: any one of the new services drifting
out of shape breaks this test, not just its own unit tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from verge_compliance import assess, build_incident_report
from verge_connectors import demo_cmms, demo_historian
from verge_contracts import validate_stream
from verge_permit import conflict_findings
from verge_risk import STARTER_RULES, load_rules, run_stream
from verge_twin import load_plant

NOW = datetime(2026, 7, 7, tzinfo=UTC)


def _pipeline_events() -> list[dict]:
    """Stage 1 — pull canonical events from the integration hub (CMMS + historian)."""
    events = demo_cmms().pull().events + demo_historian().pull().events
    return sorted(events, key=lambda e: e["ts"])


def test_stage1_and_2_connectors_emit_contract_valid_events():
    events = _pipeline_events()
    assert events
    report = validate_stream(events)
    # Every event the connectors emit must satisfy its data contract (§14 P4).
    assert report["invalid"] == 0, report["violations"]
    assert report["valid"] == report["total"]


def _run_engine(events: list[dict]):
    plant = load_plant()
    adjacency = plant.adjacency()

    def simops(state):
        return conflict_findings(state.permits, adjacency=adjacency,
                                 now=state.now, at=state.now)

    collected: list = []
    run_stream(
        events,
        load_rules(STARTER_RULES),
        collected.append,
        thresholds=plant.thresholds_by_kind(),
        detectors=[simops],
        window=12,
        min_confidence=0.0,
    )
    return collected


def test_stage3_engine_produces_compound_and_simops_findings():
    findings = _run_engine(_pipeline_events())
    assert findings
    titles = [f.title for f in findings]
    # Hot-work + rising flammable gas in B-04 (permit from CMMS, reading from historian).
    assert any("Hot work" in t for t in titles)
    # Isolation-breach rule (H1-E) firing on the CMMS isolation permit + rising LEL.
    assert any("isolation" in t.lower() for t in titles)
    # SIMOPS across adjacent zones (hot-work B-04 ∩ confined-space B-05).
    assert any(t.startswith("SIMOPS") for t in titles)


def test_stage4_incident_report_is_hash_chained():
    findings = _run_engine(_pipeline_events())
    gas = next(f for f in findings if "Hot work" in f.title)
    report = build_incident_report(
        gas,
        audit_trail=[{"kind": "finding-created", "actor": "risk-engine",
                      "timestamp": gas.created_at.isoformat(),
                      "payload": {"findingId": gas.finding_id}}],
        created_at=NOW,
        audit_head="pipeline-head",
    )
    assert len(report.hash) == 64
    assert "VC-HOT-WORK" in report.clause_ids  # regulatory linkage resolved


def test_stage5_compliance_assessment_over_pipeline_plant():
    plant = load_plant()
    result = assess(plant, load_rules(STARTER_RULES))
    assert 0.0 < result.coverage_ratio <= 1.0
    # The pipeline plant demonstrates hot-work + gas detection controls.
    caps = {r.clause.capability: r.status for r in result.results}
    assert caps["hot-work-control"] == "satisfied"
    assert caps["gas-detection"] == "satisfied"
