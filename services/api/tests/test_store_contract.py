"""Both stores must behave identically — the in-memory and SQL backends are
interchangeable behind StoreProtocol. Run the same assertions against each.

If VERGE_TEST_DB_URL is set (CI's Postgres job), a third 'pg' backend runs the
same contract against a real Postgres, so the durable path is verified on the
production database, not only SQLite."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from verge_api import db
from verge_api.sql_store import SqlStore
from verge_api.store import InMemoryStore
from verge_api.store_base import StoreProtocol
from verge_schema.enums import DataQuality, FeedbackVerdict
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding

T0 = datetime(2025, 1, 13, 6, 30, tzinfo=UTC)
_PG_URL = os.environ.get("VERGE_TEST_DB_URL")
_PARAMS = ["memory", "sql"] + (["pg"] if _PG_URL else [])


@pytest.fixture(params=_PARAMS)
def store(request, tmp_path) -> StoreProtocol:
    if request.param == "memory":
        return InMemoryStore()
    if request.param == "sql":
        return SqlStore(f"sqlite:///{tmp_path}/contract.db")
    # pg: ensure schema exists, then truncate for per-test isolation.
    engine = db.make_engine(_PG_URL)
    with engine.begin() as conn:
        for tbl in ("finding", "finding_feedback", "audit_entry", "sensor_health", "outbox_event"):
            conn.execute(text(f"TRUNCATE TABLE {tbl} RESTART IDENTITY"))
    return SqlStore(_PG_URL)


def _f(fid: str, *, shadow: bool = False, state: S = S.NEW, band: str = "NEAR",
       offset: int = 0) -> RiskFinding:
    return RiskFinding(
        finding_id=fid, created_at=T0 + timedelta(minutes=offset), zone_id="B-04",
        title=f"finding {fid}", state=state, confidence=0.85,
        lead_time_band=band, shadow=shadow, lineage=[f"reading:{fid}"],
    )


def test_satisfies_protocol(store) -> None:
    assert isinstance(store, StoreProtocol)


def test_add_get_list(store) -> None:
    store.add_finding(_f("F-1", offset=1))
    store.add_finding(_f("F-2", offset=2))
    assert store.get_finding("F-1").title == "finding F-1"
    assert store.get_finding("MISSING") is None
    ids = [f.finding_id for f in store.list_findings()]
    assert ids == ["F-2", "F-1"]  # newest first


def test_shadow_filter(store) -> None:
    store.add_finding(_f("F-live"))
    store.add_finding(_f("F-shadow", shadow=True))
    assert [f.finding_id for f in store.list_findings()] == ["F-live"]  # live only
    assert [f.finding_id for f in store.list_findings(shadow=True)] == ["F-shadow"]
    assert len(store.list_findings(shadow=None)) == 2
    assert store.shadow_summary() == {"shadow": 1, "byBand": {"NEAR": 1}}


def test_transition_persists_state_and_audits(store) -> None:
    store.add_finding(_f("F-1"))
    before = store.audit_len()
    f = store.transition("F-1", S.ACKNOWLEDGED, "maya")
    assert f.state == "acknowledged"
    assert store.get_finding("F-1").state == "acknowledged"
    assert store.audit_len() == before + 1
    assert store.audit_verify() is True


def test_feedback_and_fpr(store) -> None:
    store.add_finding(_f("F-1"))
    assert store.fpr() is None
    store.add_feedback("F-1", "maya", FeedbackVerdict.USEFUL)
    store.add_feedback("F-1", "maya", FeedbackVerdict.FALSE_ALARM, reason_code="noise")
    assert store.fpr() == 0.5


def test_sensor_health_roundtrip(store) -> None:
    store.set_sensor_health({DataQuality.LIVE: 847, DataQuality.STALE: 12})
    health = store.get_sensor_health()
    assert health[DataQuality.LIVE] == 847
    assert health[DataQuality.STALE] == 12


def test_audit_chain_links_and_verifies(store) -> None:
    for i in range(3):
        store.add_finding(_f(f"F-{i}", offset=i))
    assert store.audit_len() == 3
    assert store.audit_verify() is True
    assert store.audit_head() != "0" * 64
