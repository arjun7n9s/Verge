"""Stream runner re-evaluates on voice/vision (Phase 2), not only readings."""

from verge_risk import STARTER_RULES, load_rules, run_stream


def test_voice_event_alone_can_emit_with_permit() -> None:
    events = [
        {
            "type": "permit",
            "ts": "2025-01-13T06:40:00+00:00",
            "permitId": "PW-1",
            "kind": "hot-work",
            "zoneId": "B-04",
            "validFrom": "2025-01-13T06:00:00+00:00",
            "validTo": "2025-01-13T12:00:00+00:00",
        },
        {
            "type": "voice-event",
            "ts": "2025-01-13T06:44:00+00:00",
            "eventId": "VE-1",
            "transcript": "gas smell near B-04",
            "zoneId": "B-04",
            "hazards": ["gas", "smell"],
            "source": "radio",
        },
    ]
    out: list = []
    n = run_stream(events, load_rules(STARTER_RULES), out.append, min_confidence=0.5)
    assert n >= 1
    assert any(any(s.kind == "voice" for s in f.contributing_signals) for f in out)
