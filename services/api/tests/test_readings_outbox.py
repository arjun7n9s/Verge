"""Reading ingest outbox enqueue test."""

from datetime import UTC, datetime

from verge_api.sql_store import SqlStore

T0 = datetime(2025, 1, 13, 6, 30, tzinfo=UTC)


def test_enqueue_reading_outbox(tmp_path) -> None:
    store = SqlStore(f"sqlite:///{tmp_path}/verge.db")
    event = {
        "type": "reading",
        "ts": "2025-01-13T06:30:00+00:00",
        "sensorId": "LEL-04",
        "kind": "gas-lel",
        "unit": "%LEL",
        "zoneId": "B-04",
        "value": 12.0,
        "eventId": "evt-1",
    }
    store.enqueue_reading(event, skip_redpanda=True)
    assert store.outbox_pending() == 1

    published: list[tuple[str, dict]] = []

    def capture(kind: str, payload: dict) -> None:
        published.append((kind, payload))

    assert store.drain_outbox(capture) == 1
    assert published[0][0] == "reading-ingested"
    assert published[0][1]["event"]["sensorId"] == "LEL-04"
    assert published[0][1]["skipRedpanda"] is True
