"""The provider contract: default is safe (null), and failures degrade not raise."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from verge_llm import (
    Completion,
    LLMProvider,
    Message,
    NullProvider,
    OpenAICompatProvider,
    provider_from_env,
)


def test_default_is_null_provider() -> None:
    p = provider_from_env({})
    assert isinstance(p, NullProvider)
    assert p.healthy() is True


def test_null_provider_degrades_cleanly() -> None:
    p = NullProvider()
    c = p.complete([Message(role="user", content="summarize the convergence")])
    assert isinstance(c, Completion)
    assert c.degraded is True
    assert "summarize the convergence"[:10] in c.text


def test_providers_satisfy_protocol() -> None:
    assert isinstance(NullProvider(), LLMProvider)


def test_unreachable_remote_degrades_not_raises() -> None:
    # Points at an unroutable port; complete() must return degraded, never raise.
    p = OpenAICompatProvider(
        name="aimlapi",
        base_url="http://127.0.0.1:1/v1",
        api_key="x",
        default_model="claude-sonnet-4-5",
        timeout_s=0.2,
        health_timeout_s=0.2,
        health_ttl_s=0.0,
    )
    c = p.complete([Message(role="user", content="hi")])
    assert c.degraded is True
    assert "unreachable" in (c.reason or "")


def test_env_selects_aimlapi() -> None:
    p = provider_from_env({"VERGE_LLM_PROVIDER": "aimlapi", "AIMLAPI_API_KEY": "k"})
    assert p.name == "aimlapi"


def test_healthy_probes_chat_completions_not_models() -> None:
    p = OpenAICompatProvider(
        name="aimlapi",
        base_url="https://example.test/v1",
        api_key="k",
        default_model="claude-sonnet-4-5",
        health_timeout_s=1.0,
        health_ttl_s=0.0,
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_resp
    mock_client.get.side_effect = AssertionError("healthy must not GET /models")

    with patch.object(p, "_client", return_value=mock_client):
        assert p.healthy() is True

    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "/chat/completions"
    assert kwargs["json"]["max_tokens"] == 1
    mock_client.get.assert_not_called()


def test_healthy_false_when_chat_probe_fails() -> None:
    p = OpenAICompatProvider(
        name="aimlapi",
        base_url="https://example.test/v1",
        api_key="k",
        default_model="claude-sonnet-4-5",
        health_ttl_s=0.0,
    )
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.side_effect = TimeoutError("slow")

    with patch.object(p, "_client", return_value=mock_client):
        assert p.healthy() is False
    assert p.last_fail_reason
    assert "TimeoutError" in p.last_fail_reason


def test_healthy_ttl_cache_skips_second_probe() -> None:
    p = OpenAICompatProvider(
        name="aimlapi",
        base_url="https://example.test/v1",
        api_key="k",
        default_model="claude-sonnet-4-5",
        health_ttl_s=60.0,
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_resp

    with patch.object(p, "_client", return_value=mock_client):
        assert p.healthy() is True
        assert p.healthy() is True

    assert p._health_probe_count == 1
    assert mock_client.post.call_count == 1
