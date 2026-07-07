"""Compliance API — OISD/Factory Act/DGMS gap assessment + evidence pack (§5).

Deterministic and LLM-free: the assessment is reproducible from the commissioned
plant model + the adopted rule library, and the evidence pack is hash-chained
against the live audit head (P6). This surfaces the same gaps a regulator would
ask about, with a tamper-evident manifest to back them.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from verge_compliance import (
    assess,
    build_compliance_pack,
    build_incident_report,
    changes_since_prior,
    gap_findings,
)
from verge_risk import STARTER_RULES, load_rules
from verge_twin import load_plant
from verge_twin.plant import DEMO_PLANT

router = APIRouter(tags=["compliance"])


def _plant_and_rules():
    # The pilot runs one commissioned plant; the demo plant stands in until a
    # site uploads its own. Rules come from the adopted starter library (§14.5).
    return load_plant(DEMO_PLANT), load_rules(STARTER_RULES)


@router.get("/compliance/report")
def compliance_report(request: Request) -> dict:
    """Full clause-by-clause gap assessment plus a hash-chained evidence pack."""
    store = request.app.state.store
    plant, rules = _plant_and_rules()
    report = assess(plant, rules)
    finding_ids = [f.finding_id for f in store.list_findings(shadow=None)]
    pack = build_compliance_pack(
        report,
        created_at=datetime.now(UTC),
        finding_ids=finding_ids,
        audit_head=store.audit_head(),
    )
    return {**report.to_dict(), "evidencePack": pack.to_dict()}


@router.get("/compliance/gaps")
def compliance_gaps(request: Request) -> dict:
    """Just the open gaps, as regulatory-gap payloads (for the console badge)."""
    plant, rules = _plant_and_rules()
    report = assess(plant, rules)
    return {"plant": report.plant, "gaps": gap_findings(report)}


@router.get("/compliance/changes")
def compliance_changes(request: Request) -> dict:
    """What changed in the regulatory clause library vs. the certified baseline."""
    return changes_since_prior()


@router.get("/findings/{finding_id}/incident-report")
def incident_report(finding_id: str, request: Request) -> dict:
    """Final, audit-backed, hash-chained incident report for a finding (§14 Phase 3)."""
    store = request.app.state.store
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    trail = [
        e for e in store.audit_entries(limit=100_000)
        if (e.get("payload") or {}).get("findingId") == finding_id
    ]
    report = build_incident_report(
        finding,
        audit_trail=trail,
        created_at=datetime.now(UTC),
        audit_head=store.audit_head(),
    )
    return report.to_dict()
