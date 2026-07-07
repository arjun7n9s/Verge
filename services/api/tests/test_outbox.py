"""Transactional outbox tests."""

from datetime import UTC, datetime

from verge_api.sql_store import SqlStore
from verge_schema.enums import FindingState as S
from verge_schema.findings import RiskFinding

T0 = datetime(2025, 1, 13, 6, 30, tzinfo=UTC)


def _f(fid: str) -> RiskFinding:
    return RiskFinding(
        finding_id=fid,
        created_at=T0,
        zone_id="B-04",
        title=f"f {fid}",
        state=S.NEW,
        confidence=0.85,
        lead_time_band="NEAR",
        lineage=[f"reading:{fid}"],
    )


def test_add_finding_enqueues_outbox_before_drain(tmp_path) -> None:
    store = SqlStore(f"sqlite:///{tmp_path}/verge.db")
    store.add_finding(_f("F-OX"))
    assert store.outbox_pending() == 1

    published: list[tuple[str, dict]] = []

    def capture(kind: str, payload: dict) -> None:
        published.append((kind, payload))

    n = store.drain_outbox(capture)
    assert n == 1
    assert store.outbox_pending() == 0
    assert published[0][0] == "findings-updated"
    assert published[0][1]["findingId"] == "F-OX"


def test_finding_and_audit_share_transaction_on_add(tmp_path) -> None:
    store = SqlStore(f"sqlite:///{tmp_path}/verge.db")
    store.add_finding(_f("F-A"))
    assert store.get_finding("F-A") is not None
    assert store.audit_len() == 1
    assert store.audit_verify() is True

    store2 = SqlStore(f"sqlite:///{tmp_path}/verge.db")
    assert store2.outbox_pending() == 1
