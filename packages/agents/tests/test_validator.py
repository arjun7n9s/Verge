"""Deterministic brief validator — invented tags and uncited barriers."""

from __future__ import annotations

from verge_agents import TwinCatalog, validate_brief


def _catalog() -> TwinCatalog:
    return TwinCatalog(
        zone_ids=frozenset({"B-04", "B-03"}),
        equipment_ids=frozenset({"EQ-OVEN-1"}),
        sensor_ids=frozenset({"LEL-04A"}),
    )


def test_invented_equipment_tag_demotes_barrier():
    brief = {
        "summary": "Hot work in B-04 near EQ-OVEN-1.",
        "hypotheses": [],
        "recommendedBarriers": [
            {
                "action": "Isolate FAKE-99 before restart",
                "urgency": "immediate",
                "rationale": "unknown skid",
                "supportedBy": "get_zone_context",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    out, report = validate_brief(
        brief, _catalog(), evidence_tools=["get_zone_context"]
    )
    assert report.ok is False
    assert "FAKE-99" in report.invented_tags
    assert out["recommendedBarriers"] == []
    assert any("FAKE-99" in q for q in out["openQuestions"])


def test_known_tags_with_evidence_keep_barrier():
    brief = {
        "summary": "Rising LEL on LEL-04A in B-04.",
        "hypotheses": [],
        "recommendedBarriers": [
            {
                "action": "Suspend hot work near EQ-OVEN-1 in B-04",
                "urgency": "immediate",
                "rationale": "SIMOPS with live LEL",
                "supportedBy": "get_active_permits",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    out, report = validate_brief(
        brief, _catalog(), evidence_tools=["get_active_permits"]
    )
    assert report.ok is True
    assert report.invented_tags == []
    assert len(out["recommendedBarriers"]) == 1


def test_uncited_barrier_demoted():
    brief = {
        "summary": "Watch band in B-04.",
        "hypotheses": [],
        "recommendedBarriers": [
            {
                "action": "Increase patrols in B-04",
                "urgency": "this-shift",
                "rationale": "gut feel",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    out, report = validate_brief(brief, _catalog(), evidence_tools=["get_finding"])
    assert len(out["recommendedBarriers"]) == 0
    assert report.demoted_barriers
    assert report.demoted_barriers[0]["reason"] == "uncited"


def test_fake_supported_by_without_tool_or_ref_is_demoted():
    brief = {
        "summary": "Watch band in B-04.",
        "hypotheses": [],
        "recommendedBarriers": [
            {
                "action": "Increase patrols in B-04",
                "urgency": "this-shift",
                "rationale": "sounds right",
                "supportedBy": "telemetry",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    out, report = validate_brief(
        brief, _catalog(), evidence_tools=["get_finding"], known_refs=["VE-ABC"]
    )
    assert out["recommendedBarriers"] == []
    assert report.demoted_barriers[0]["reason"] == "uncited"


def test_known_ref_in_supported_by_keeps_barrier():
    brief = {
        "summary": "Radio report in B-04.",
        "hypotheses": [],
        "recommendedBarriers": [
            {
                "action": "Pause hot work in B-04",
                "urgency": "immediate",
                "rationale": "gas smell on radio",
                "supportedBy": "VE-ABC123",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    out, report = validate_brief(
        brief,
        _catalog(),
        evidence_tools=["get_recent_voice_events"],
        known_refs=["VE-ABC123"],
    )
    assert len(out["recommendedBarriers"]) == 1
    assert report.ok is True


def test_empty_catalog_still_flags_unknown_tags():
    brief = {
        "summary": "Mention FAKE-99 freely.",
        "hypotheses": [],
        "recommendedBarriers": [
            {
                "action": "Check FAKE-99",
                "urgency": "planned",
                "rationale": "x",
                "supportedBy": "search_plant_docs",
            }
        ],
        "regulatoryRefs": [],
        "openQuestions": [],
    }
    out, report = validate_brief(
        brief, TwinCatalog.empty(), evidence_tools=["search_plant_docs"]
    )
    assert "FAKE-99" in report.invented_tags
    assert out["recommendedBarriers"] == []
