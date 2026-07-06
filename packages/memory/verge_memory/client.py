"""Cognee Cloud HTTP client.

Cognee's current HTTP API uses tenant base URLs, `X-Api-Key`, and `/api/v1/*`
paths. This client is intentionally small and defensive: missing credentials,
network failures, and non-2xx responses become degraded results instead of
exceptions leaking into the API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CogneeSettings:
    enabled: bool = False
    base_url: str | None = None
    api_key: str | None = None
    timeout_s: float = 20.0

    @classmethod
    def from_env(cls, env: dict[str, str]) -> CogneeSettings:
        enabled = env.get("VERGE_COGNEE_ENABLED", "").lower() in TRUE_VALUES
        base_url = (
            env.get("COGNEE_BASE_URL")
            or env.get("COGNEE_SERVICE_URL")
            or env.get("COGNEE_API_BASE_URL")
        )
        timeout = float(env.get("COGNEE_TIMEOUT_S", "20"))
        return cls(
            enabled=enabled,
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=env.get("COGNEE_API_KEY"),
            timeout_s=timeout,
        )

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.base_url) and bool(self.api_key)

    def missing_reason(self) -> str | None:
        if not self.enabled:
            return "VERGE_COGNEE_ENABLED is not true"
        if not self.base_url:
            return "missing COGNEE_BASE_URL or COGNEE_SERVICE_URL"
        if not self.api_key:
            return "missing COGNEE_API_KEY"
        return None


@dataclass(frozen=True)
class CogneeResult:
    ok: bool
    data: Any = None
    degraded: bool = False
    reason: str | None = None

    @classmethod
    def success(cls, data: Any = None) -> CogneeResult:
        return cls(ok=True, data=data, degraded=False)

    @classmethod
    def fail(cls, reason: str) -> CogneeResult:
        return cls(ok=False, data=None, degraded=True, reason=reason)


@dataclass
class CogneeClient:
    settings: CogneeSettings
    client: httpx.Client | None = None
    _owns_client: bool = field(default=False, init=False)

    @classmethod
    def from_env(cls, env: dict[str, str]) -> CogneeClient:
        return cls(CogneeSettings.from_env(env))

    def __enter__(self) -> CogneeClient:
        if self.client is None and self.settings.base_url:
            self.client = httpx.Client(
                base_url=self.settings.base_url,
                headers=self._headers(),
                timeout=self.settings.timeout_s,
            )
            self._owns_client = True
        return self

    def __exit__(self, *_exc) -> None:
        if self._owns_client and self.client is not None:
            self.client.close()
        self.client = None
        self._owns_client = False

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.settings.api_key:
            headers["X-Api-Key"] = self.settings.api_key
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> CogneeResult:
        if reason := self.settings.missing_reason():
            return CogneeResult.fail(reason)

        close_after = False
        client = self.client
        if client is None:
            client = httpx.Client(
                base_url=self.settings.base_url,
                headers=self._headers(),
                timeout=self.settings.timeout_s,
            )
            close_after = True

        try:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            if not response.content:
                return CogneeResult.success({})
            return CogneeResult.success(response.json())
        except Exception as exc:
            return CogneeResult.fail(f"cognee {method} {path} failed: {type(exc).__name__}")
        finally:
            if close_after:
                client.close()

    def create_dataset(self, name: str) -> CogneeResult:
        return self._request("POST", "/api/v1/datasets/", json={"name": name})

    def add_text(self, dataset: str, text: str, *, filename: str) -> CogneeResult:
        files = {"data": (filename, text.encode("utf-8"), "text/markdown")}
        data = {"datasetName": dataset, "run_in_background": "false"}
        return self._request("POST", "/api/v1/add", data=data, files=files)

    def cognify(self, dataset: str) -> CogneeResult:
        return self._request(
            "POST",
            "/api/v1/cognify",
            json={"datasets": [dataset], "run_in_background": False},
        )

    def search(self, dataset: str, query: str, *, top_k: int = 5) -> CogneeResult:
        return self._request(
            "POST",
            "/api/v1/search",
            json={
                "query": query,
                "datasets": [dataset],
                "search_type": "GRAPH_COMPLETION",
                "only_context": True,
                "include_references": True,
                "top_k": top_k,
            },
        )
