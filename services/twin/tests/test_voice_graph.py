"""Neo4j VoiceEvent ABOUT edges — degrade without Neo4j."""

from datetime import UTC, datetime

from verge_schema.events import VoiceEvent
from verge_twin.voice_graph import sync_voice_event


def test_sync_voice_event_degrades_without_neo4j() -> None:
    ev = VoiceEvent(
        event_id="VE-TEST",
        ts=datetime.now(UTC),
        transcript="gas smell B-04",
        zone_id="B-04",
        hazards=["gas"],
        equipment_ids=["EQ-P-3"],
    )
    out = sync_voice_event(ev, env={})
    assert out["degraded"] is True
    assert "neo4j" in out["reason"]
