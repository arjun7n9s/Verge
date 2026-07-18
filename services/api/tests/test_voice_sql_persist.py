"""Voice events survive SQL-store restart (fusion evidence durability)."""

from __future__ import annotations

from verge_api.sql_store import SqlStore
from verge_api.voice_events import VoiceEventBuffer


def test_voice_events_hydrate_after_restart(tmp_path) -> None:
    url = f"sqlite:///{tmp_path}/voice.db"
    store1 = SqlStore(url)
    buf1 = VoiceEventBuffer(store1.engine)
    ev = buf1.record(
        transcript="gas smell near battery B-04, pause hot work",
        zone_id="B-04",
        source="radio",
        structured={"hazards": ["gas"], "zones": ["B-04"]},
    )
    assert ev.event_id.startswith("VE-")
    assert len(buf1.events) == 1
    del buf1
    del store1

    store2 = SqlStore(url)
    buf2 = VoiceEventBuffer(store2.engine)
    assert len(buf2.events) == 1
    loaded = buf2.events[0]
    assert loaded.event_id == ev.event_id
    assert loaded.zone_id == "B-04"
    assert "gas" in loaded.hazards
    assert "B-04" in loaded.transcript
