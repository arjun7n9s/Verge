"""Backup / restore audit-chain verification (spec §14.6)."""

from __future__ import annotations

import copy

from fastapi.testclient import TestClient
from verge_api.backup import snapshot_audit, verify_snapshot
from verge_api.main import app

client = TestClient(app)


def test_snapshot_round_trips_and_verifies():
    snap = client.get("/api/ops/backup").json()
    assert snap["count"] >= 1
    assert len(snap["snapshotHash"]) == 64
    report = client.post("/api/ops/backup/verify", json=snap).json()
    assert report["verified"] is True
    assert report["headMatches"] and report["snapshotHashMatches"]


def test_tampered_middle_entry_is_rejected():
    snap = copy.deepcopy(client.get("/api/ops/backup").json())
    assert snap["count"] >= 2
    # Tamper a payload in the middle; the linkage walk must break.
    snap["entries"][0]["payload"] = {"tampered": True}
    report = client.post("/api/ops/backup/verify", json=snap).json()
    assert report["verified"] is False


def test_tampered_last_entry_is_rejected_by_head_mismatch():
    snap = copy.deepcopy(snapshot_audit(app.state.store))
    snap["entries"][-1]["payload"] = {"tampered": "last"}
    report = verify_snapshot(snap)
    # Middle-linkage may pass, but the recomputed head no longer matches.
    assert report["verified"] is False


def test_snapshot_hash_detects_reordering():
    snap = copy.deepcopy(snapshot_audit(app.state.store))
    if snap["count"] >= 2:
        snap["entries"][0]["actor"] = snap["entries"][0]["actor"] + "-x"
        assert verify_snapshot(snap)["verified"] is False


def test_expected_head_anchor_rejects_reforged_chain():
    # A fully self-consistent snapshot verifies on internal consistency alone...
    snap = snapshot_audit(app.state.store)
    assert verify_snapshot(snap)["verified"] is True
    # ...but against a trusted out-of-band head it must match that head.
    good = verify_snapshot(snap, expected_head=snap["head"])
    assert good["verified"] is True and good["anchored"] is True
    bad = verify_snapshot(snap, expected_head="0" * 64)
    assert bad["verified"] is False and bad["anchorMatches"] is False


def test_verify_route_accepts_expected_head():
    snap = client.get("/api/ops/backup").json()
    snap["expectedHead"] = "0" * 64
    report = client.post("/api/ops/backup/verify", json=snap).json()
    assert report["verified"] is False and report["anchored"] is True
