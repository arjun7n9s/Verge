from datetime import UTC, datetime

import httpx
from verge_memory.client import CogneeClient, CogneeSettings
from verge_memory.datasets import dataset_name
from verge_memory.retrieve import context_for_finding
from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding


def _finding() -> RiskFinding:
    return RiskFinding(
        finding_id="F-CONV-07",
        created_at=datetime(2025, 1, 13, 6, 44, tzinfo=UTC),
        zone_id="B-04",
        title="Hot work + rising flammable gas during shift changeover",
        state=FindingState.NEW,
        confidence=0.85,
        contributing_signals=[
            ContributingSignal(kind="permit", ref_id="PW-1", summary="hot-work permit active"),
            ContributingSignal(kind="reading", ref_id="LEL-04", summary="LEL rising"),
        ],
        lead_time_band=LeadTimeBand.NEAR,
        estimate_quality=EstimateQuality.HIGH,
        lineage=["permit:PW-1", "reading:LEL-04"],
    )


def test_dataset_name_uses_prefix_and_site() -> None:
    assert dataset_name({"COGNEE_DATASET_PREFIX": "verge mem", "VERGE_SITE_ID": "Vizag/1"}) == (
        "verge-mem-Vizag-1"
    )


def test_missing_cognee_degrades_empty() -> None:
    body = context_for_finding(_finding(), env={})
    assert body["findingId"] == "F-CONV-07"
    assert body["degraded"] is True
    assert body["similarIncidents"] == []
    assert "reason" in body


def test_client_uses_v1_cognee_endpoints() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        base_url="https://tenant.aws.cognee.ai",
        headers={"X-Api-Key": "key"},
        transport=transport,
    )
    cognee = CogneeClient(
        CogneeSettings(enabled=True, base_url="https://tenant.aws.cognee.ai", api_key="key"),
        client=client,
    )

    assert cognee.create_dataset("verge-test").ok
    assert cognee.add_text("verge-test", "body", filename="body.md").ok
    assert cognee.cognify("verge-test").ok
    assert cognee.search("verge-test", "query").ok
    assert seen == [
        ("POST", "/api/v1/datasets/"),
        ("POST", "/api/v1/add"),
        ("POST", "/api/v1/cognify"),
        ("POST", "/api/v1/search"),
    ]


def test_context_retrieval_with_mocked_cognee() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/search":
            return httpx.Response(200, json=["matching context"])
        return httpx.Response(200, json={"ok": True})

    http = httpx.Client(
        base_url="https://tenant.aws.cognee.ai",
        headers={"X-Api-Key": "key"},
        transport=httpx.MockTransport(handler),
    )
    client = CogneeClient(
        CogneeSettings(enabled=True, base_url="https://tenant.aws.cognee.ai", api_key="key"),
        client=http,
    )
    env = {
        "VERGE_COGNEE_ENABLED": "true",
        "COGNEE_BASE_URL": "https://tenant.aws.cognee.ai",
        "COGNEE_API_KEY": "key",
        "VERGE_SITE_ID": "unit-test",
    }

    body = context_for_finding(_finding(), client=client, env=env)
    assert body["degraded"] is False
    assert body["similarIncidents"][0]["excerpt"] == "matching context"
    assert body["regulatoryClauses"][0]["excerpt"] == "matching context"
    assert body["plantHistory"][0]["summary"] == "matching context"
    assert calls.count("/api/v1/search") == 3
