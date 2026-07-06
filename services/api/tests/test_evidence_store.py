"""Tests for optional MinIO evidence upload."""

from datetime import UTC, datetime

from verge_api.evidence_store import upload_evidence_manifest
from verge_schema.audit import EvidencePack


def _pack() -> EvidencePack:
    return EvidencePack(
        pack_id="EP-TEST",
        finding_id="F-TEST",
        items=["reading:LEL-04"],
        manifest_hash="abc123",
        created_at=datetime(2025, 1, 13, 7, 0, tzinfo=UTC),
    )


def test_upload_skips_without_minio_env() -> None:
    assert upload_evidence_manifest(_pack(), env={}) is None


def test_upload_skips_when_minio_incomplete() -> None:
    env = {"MINIO_ENDPOINT": "localhost:9000", "MINIO_ACCESS_KEY": "verge"}
    assert upload_evidence_manifest(_pack(), env=env) is None
