"""Orchestrator is advisory-only, multilingual, lineage-citing, never auto-submits."""

from datetime import UTC, datetime

from verge_orchestrator import (
    build_evidence_pack,
    draft_messages,
    manifest_hash,
    recommend_action,
    respond,
)
from verge_schema.enums import LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding

AT = datetime(2025, 1, 13, 6, 44, tzinfo=UTC)


def _finding(**kw) -> RiskFinding:
    base = dict(
        finding_id="F-CONV-07", created_at=AT, zone_id="B-04",
        title="Hot work + rising flammable gas during shift changeover",
        confidence=0.85, lead_time_band=LeadTimeBand.NEAR,
        contributing_signals=[
            ContributingSignal(kind="permit", ref_id="PW-2025-0142", summary="hot-work permit"),
            ContributingSignal(kind="reading", ref_id="LEL-04", summary="gas-lel 91.5 rising"),
        ],
        lineage=["permit:PW-2025-0142", "reading:LEL-04"],
    )
    base.update(kw)
    return RiskFinding(**base)


def test_permit_finding_recommends_pause_and_is_advisory() -> None:
    a = recommend_action(_finding())
    assert a.kind == "recommend-permit-pause"
    assert a.advisory is True  # P8: never executed by Verge


def test_no_permit_imminent_recommends_evacuate() -> None:
    f = _finding(contributing_signals=[
        ContributingSignal(kind="reading", ref_id="LEL-09", summary="rising"),
    ], lead_time_band=LeadTimeBand.IMMINENT, lineage=["reading:LEL-09"])
    assert recommend_action(f).kind == "recommend-evacuate-zone"


def test_alert_is_multilingual_and_mentions_zone() -> None:
    msgs = draft_messages(_finding(), "pause the permit")
    assert set(msgs) == {"en", "hi", "te"}
    assert all("B-04" in m for m in msgs.values())


def test_alert_renders_band_value_not_enum_repr() -> None:
    # Guards the use_enum_values contract: the band must format as "NEAR",
    # never "LeadTimeBand.NEAR", in every language.
    msgs = draft_messages(_finding(lead_time_band=LeadTimeBand.NEAR), "pause the permit")
    for body in msgs.values():
        assert "NEAR" in body
        assert "LeadTimeBand" not in body


def test_evidence_manifest_hash_is_order_independent() -> None:
    assert manifest_hash(["a", "b"]) == manifest_hash(["b", "a"])
    pack = build_evidence_pack(_finding(), created_at=AT)
    assert pack.manifest_hash == manifest_hash(pack.items)


def test_respond_drafts_everything_without_executing() -> None:
    r = respond(_finding(), at=AT)  # default NullProvider -> degraded narrative
    assert r.action.advisory is True
    assert r.alert.languages == ["en", "hi", "te"]
    assert r.report.submitted is False  # P8
    assert r.report.narrative_degraded is True  # no LLM configured
    # report cites the lineage (P3)
    assert "permit:PW-2025-0142" in r.report.cited
    assert "NOT submitted" in r.report.markdown
    # audit payloads are data for the caller to hash-chain, not side effects
    kinds = {p["kind"] for p in r.audit_payloads()}
    assert kinds == {"recommendation", "alert-drafted", "evidence-pack"}
