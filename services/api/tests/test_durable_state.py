"""Permit and reading persistence when VERGE_STORE=sql."""

from datetime import UTC, datetime, timedelta

from verge_api import db
from verge_api.permits_registry import PermitRegistry
from verge_api.reading_buffer import ReadingBuffer
from verge_schema.core import Permit


def test_permits_survive_registry_restart(tmp_path) -> None:
    url = f"sqlite:///{tmp_path}/verge.db"
    engine = db.make_engine(url)
    now = datetime.now(UTC)

    r1 = PermitRegistry(engine)
    r1.upsert(
        Permit(
            permit_id="PW-SQL-1",
            kind="hot-work",
            zone_id="B-04",
            valid_from=now - timedelta(minutes=5),
            valid_to=now + timedelta(hours=2),
            status="open",
        )
    )
    del r1

    r2 = PermitRegistry(engine)
    assert any(p.permit_id == "PW-SQL-1" for p in r2.list_active(now=now))


def test_readings_survive_buffer_restart(tmp_path) -> None:
    url = f"sqlite:///{tmp_path}/verge.db"
    engine = db.make_engine(url)

    b1 = ReadingBuffer(engine)
    b1.ingest({
        "type": "reading",
        "ts": "2025-01-13T07:00:00+00:00",
        "sensorId": "LEL-PERSIST",
        "kind": "gas-lel",
        "unit": "%LEL",
        "zoneId": "B-04",
        "value": 88.5,
    })
    del b1

    b2 = ReadingBuffer(engine)
    points = list(b2._by_sensor.get("LEL-PERSIST", []))
    assert len(points) == 1
    assert points[0]["value"] == 88.5
