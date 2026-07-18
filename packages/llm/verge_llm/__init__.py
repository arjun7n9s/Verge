"""Swappable LLM provider abstraction (spec §7, P1/P2)."""

from __future__ import annotations

import os

from .base import Completion, LLMProvider, Message, ToolCall
from .providers import NullProvider, OpenAICompatProvider

__all__ = [
    "Completion",
    "LLMProvider",
    "Message",
    "NullProvider",
    "OpenAICompatProvider",
    "ToolCall",
    "provider_from_env",
]
__version__ = "0.3.0"


def provider_from_env(env: dict[str, str] | None = None) -> LLMProvider:
    """Build the configured provider. Defaults to NullProvider so a fresh
    checkout and the air-gapped safety core run with no credentials."""
    # Empty dict is an explicit override (do not fall through to process env).
    if env is None:
        env = dict(os.environ)
    kind = env.get("VERGE_LLM_PROVIDER", "null").lower()

    health_timeout = float(env.get("VERGE_LLM_HEALTH_TIMEOUT_S", "3"))
    health_ttl = float(env.get("VERGE_LLM_HEALTH_TTL_S", "45"))
    timeout = float(env.get("VERGE_LLM_TIMEOUT_S", "20"))

    if kind == "aimlapi":
        return OpenAICompatProvider(
            name="aimlapi",
            base_url=env.get("AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1"),
            api_key=env.get("AIMLAPI_API_KEY"),
            default_model=env.get("VERGE_LLM_SYNTHESIS_MODEL", "claude-sonnet-4-5"),
            timeout_s=timeout,
            health_timeout_s=health_timeout,
            health_ttl_s=health_ttl,
        )
    if kind in {"ollama", "vllm"}:
        return OpenAICompatProvider(
            name=kind,
            base_url=env.get("VERGE_LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=env.get("VERGE_LLM_API_KEY"),
            default_model=env.get("VERGE_LLM_SYNTHESIS_MODEL", "llama3.1:8b"),
            timeout_s=timeout,
            health_timeout_s=health_timeout,
            health_ttl_s=health_ttl,
        )
    return NullProvider()
