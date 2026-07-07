"""Edge gateway autonomy wiring."""

from __future__ import annotations

from verge_edge.autonomy import EdgeAutonomy


def test_autonomy_offline_local_evaluate() -> None:
    autonomy = EdgeAutonomy(lambda events: list(events))

    sent: list[dict] = []

    def sink(e: dict) -> None:
        sent.append(e)

    event = {
        "type": "reading",
        "kind": "gas-lel",
        "sensorId": "LEL-04",
        "zoneId": "B-04",
        "value": 91,
    }
    autonomy.ingest(event, sink)
    assert sent == [event]

    autonomy.go_offline()
    autonomy.ingest({"type": "reading", "value": 2}, sink)
    assert len(sent) == 1
    local = autonomy.evaluate_local()
    assert len(local) == 1
