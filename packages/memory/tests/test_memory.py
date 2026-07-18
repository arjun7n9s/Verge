from datetime import UTC, datetime

import httpx
from verge_llm import Completion
from verge_memory.client import CogneeClient, CogneeSettings
from verge_memory.datasets import dataset_name
from verge_memory.ingest import ingest_feedback
from verge_memory.query import query_memory
from verge_memory.retrieve import context_for_finding
from verge_memory.status import dataset_health
from verge_schema.enums import EstimateQuality, FindingState, LeadTimeBand
from verge_schema.findings import ContributingSignal, RiskFinding


class _FakeLLM:
    def __init__(self, answer: str = "", degraded: bool = False) -> None:
        self.name = "fake"
        self.answer = answer
        self.degraded = degraded
        self.calls: list = []

    def complete(self, messages, *, model=None, max_tokens=512, temperature=0.2):
        self.calls.append(messages)
        return Completion(text=self.answer, model=model or "fake", degraded=self.degraded)

    def healthy(self) -> bool:
        return True


def _mocked_cognee_client(env_site: str) -> tuple[CogneeClient, dict, list]:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/search":
            return httpx.Response(
                200,
                json=[
                    {
                        "title": "Hot work control",
                        "source": "oisd-stub",
                        "text": "Pause hot work when gas readings rise near the zone.",
                    }
                ],
            )
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
        "VERGE_SITE_ID": env_site,
    }
    return client, env, calls


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


def test_query_memory_degrades_without_cognee() -> None:
    body = query_memory("what clauses apply?", env={})
    assert body["degraded"] is True
    assert body["answer"] == ""
    assert body["citations"] == []


def test_query_memory_with_mocked_cognee() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/search":
            return httpx.Response(
                200,
                json=[
                    {
                        "title": "Hot work control",
                        "source": "oisd-stub",
                        "text": "Pause hot work when gas readings rise near the zone.",
                    }
                ],
            )
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
        "VERGE_SITE_ID": "query-test",
    }

    body = query_memory("what should Maya check?", finding=_finding(), client=client, env=env)
    assert body["degraded"] is False
    assert body["answer"] == "Pause hot work when gas readings rise near the zone."
    assert body["citations"] == [
        {
            "id": "oisd-stub",
            "title": "Hot work control",
            "excerpt": "Pause hot work when gas readings rise near the zone.",
        }
    ]
    assert calls.count("/api/v1/search") == 1


def test_query_memory_synthesizes_a_grounded_answer_when_llm_reachable() -> None:
    client, env, _calls = _mocked_cognee_client("synth-test")
    llm = _FakeLLM(answer="Per [1], pause hot work as gas readings climb.")

    body = query_memory(
        "what should Maya check?", finding=_finding(), client=client, env=env, provider=llm,
    )
    assert body["degraded"] is False
    assert body["narrativeDegraded"] is False
    assert body["answer"] == "Per [1], pause hot work as gas readings climb."
    # Citations are unchanged -- synthesis adds a narrative, never replaces lineage.
    assert body["citations"][0]["excerpt"] == "Pause hot work when gas readings rise near the zone."
    # The LLM only ever sees the retrieved excerpts, never asked to invent facts.
    assert len(llm.calls) == 1
    assert "Pause hot work" in llm.calls[0][1].content


def test_query_memory_falls_back_to_raw_snippet_when_llm_degraded() -> None:
    client, env, _calls = _mocked_cognee_client("synth-degraded-test")
    llm = _FakeLLM(answer="ignored", degraded=True)

    body = query_memory(
        "what should Maya check?", finding=_finding(), client=client, env=env, provider=llm,
    )
    assert body["degraded"] is False
    assert body["narrativeDegraded"] is True
    assert body["answer"] == "Pause hot work when gas readings rise near the zone."


def test_query_memory_without_provider_uses_raw_snippet_directly() -> None:
    client, env, _calls = _mocked_cognee_client("no-provider-test")
    body = query_memory("what should Maya check?", finding=_finding(), client=client, env=env)
    assert body["narrativeDegraded"] is True
    assert body["answer"] == "Pause hot work when gas readings rise near the zone."


def test_client_retries_transient_failure() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "try later"})
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(
        base_url="https://tenant.aws.cognee.ai",
        transport=httpx.MockTransport(handler),
    )
    cognee = CogneeClient(
        CogneeSettings(
            enabled=True,
            base_url="https://tenant.aws.cognee.ai",
            api_key="key",
            retry_attempts=2,
            retry_backoff_s=0,
        ),
        client=client,
    )
    assert cognee.create_dataset("verge-test").ok
    assert attempts == 2


def test_dataset_health_degrades_without_config() -> None:
    body = dataset_health(env={})
    assert body["degraded"] is True
    assert body["configured"] is False


def test_ingest_feedback_posts_document() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(
        base_url="https://tenant.aws.cognee.ai",
        headers={"X-Api-Key": "key"},
        transport=httpx.MockTransport(handler),
    )
    cognee = CogneeClient(
        CogneeSettings(enabled=True, base_url="https://tenant.aws.cognee.ai", api_key="key"),
        client=client,
    )
    result = ingest_feedback(
        cognee,
        "verge-test",
        _finding(),
        verdict="false-alarm",
        reason_code="noise",
        reason_text="shift handover clarified the reading",
    )
    assert result.ok
    # Docs: searchable memory requires create → add → cognify.
    assert seen == ["/api/v1/datasets/", "/api/v1/add", "/api/v1/cognify"]
