"""Cognee Cloud HTTP client.

Per https://docs.cognee.ai/api-reference/introduction :
- Per-tenant base URL (e.g. https://tenant-….aws.cognee.ai)
- Auth: ``X-Api-Key``
- Paths: ``/api/v1/*`` (not ``/api/*``)
- Flow: add → cognify → search (or remember which cognifies automatically)

Missing credentials, network failures, and non-2xx become degraded results —
never exceptions into the API (P4).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def cognee_enabled_from_env(env: dict[str, str]) -> bool:
    """Explicit true/false wins; otherwise auto-on when API key + base URL exist.

    Set ``VERGE_COGNEE_ENABLED=false`` to force off even with keys present.
    """
    flag = env.get("VERGE_COGNEE_ENABLED", "").strip().lower()
    if flag in FALSE_VALUES:
        return False
    if flag in TRUE_VALUES:
        return True
    base_url = (
        env.get("COGNEE_BASE_URL")
        or env.get("COGNEE_SERVICE_URL")
        or env.get("COGNEE_API_BASE_URL")
    )
    return bool(env.get("COGNEE_API_KEY") and base_url)


@dataclass(frozen=True)
class CogneeSettings:
    enabled: bool = False
    base_url: str | None = None
    api_key: str | None = None
    timeout_s: float = 20.0
    cognify_timeout_s: float = 180.0
    retry_attempts: int = 2
    retry_backoff_s: float = 0.2

    @classmethod
    def from_env(cls, env: dict[str, str]) -> CogneeSettings:
        base_url = (
            env.get("COGNEE_BASE_URL")
            or env.get("COGNEE_SERVICE_URL")
            or env.get("COGNEE_API_BASE_URL")
        )
        timeout = float(env.get("COGNEE_TIMEOUT_S", "20"))
        cognify_timeout = float(env.get("COGNEE_COGNIFY_TIMEOUT_S", "180"))
        retries = int(env.get("COGNEE_RETRY_ATTEMPTS", "2"))
        backoff = float(env.get("COGNEE_RETRY_BACKOFF_S", "0.2"))
        return cls(
            enabled=cognee_enabled_from_env(env),
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=env.get("COGNEE_API_KEY"),
            timeout_s=timeout,
            cognify_timeout_s=cognify_timeout,
            retry_attempts=max(1, retries),
            retry_backoff_s=max(0.0, backoff),
        )

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.base_url) and bool(self.api_key)

    def missing_reason(self) -> str | None:
        if not self.enabled:
            return (
                "cognee disabled (set COGNEE_API_KEY+COGNEE_BASE_URL "
                "or VERGE_COGNEE_ENABLED=true)"
            )
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
    status_code: int | None = None

    @classmethod
    def success(cls, data: Any = None, *, status_code: int | None = None) -> CogneeResult:
        return cls(ok=True, data=data, degraded=False, status_code=status_code)

    @classmethod
    def fail(
        cls,
        reason: str,
        *,
        status_code: int | None = None,
        data: Any = None,
    ) -> CogneeResult:
        return cls(
            ok=False, data=data, degraded=True, reason=reason, status_code=status_code
        )


def _fail_from_response(method: str, path: str, response: httpx.Response) -> CogneeResult:
    detail = ""
    body: Any = None
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = str(body.get("error") or body.get("detail") or body)[:240]
        else:
            detail = str(body)[:240]
    except Exception:
        detail = (response.text or "")[:240]
    reason = f"cognee {method} {path} HTTP {response.status_code}"
    if detail:
        reason = f"{reason}: {detail}"
    # 402 is terminal per Cognee docs — surface clearly, do not look retryable.
    if response.status_code == 402:
        reason = f"cognee token budget exhausted: {detail or 'top up Cognee credits'}"
    return CogneeResult.fail(reason, status_code=response.status_code, data=body)


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

    def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: float | None = None,
        retry: bool = True,
        **kwargs: Any,
    ) -> CogneeResult:
        if reason := self.settings.missing_reason():
            return CogneeResult.fail(reason)

        close_after = False
        client = self.client
        if client is None:
            client = httpx.Client(
                base_url=self.settings.base_url,
                headers=self._headers(),
                timeout=timeout or self.settings.timeout_s,
            )
            close_after = True

        attempts = self.settings.retry_attempts if retry else 1
        try:
            last_exc: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.request(
                        method,
                        path,
                        timeout=timeout or self.settings.timeout_s,
                        **kwargs,
                    )
                    if response.status_code >= 400:
                        fail = _fail_from_response(method, path, response)
                        # Retry transient server / rate-limit errors; never 402.
                        retryable = response.status_code in {429, 502, 503, 504}
                        if retryable and attempt < attempts - 1:
                            time.sleep(self.settings.retry_backoff_s * (2**attempt))
                            continue
                        return fail
                    if not response.content:
                        return CogneeResult.success({}, status_code=response.status_code)
                    return CogneeResult.success(
                        response.json(), status_code=response.status_code
                    )
                except Exception as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        time.sleep(self.settings.retry_backoff_s * (2**attempt))
            assert last_exc is not None
            return CogneeResult.fail(
                f"cognee {method} {path} failed: {type(last_exc).__name__}: {last_exc}"
            )
        finally:
            if close_after:
                client.close()

    def health(self) -> CogneeResult:
        """Tenant health probe (docs: GET $BASE_URL/health)."""
        return self._request("GET", "/health", retry=False)

    def list_datasets(self) -> CogneeResult:
        return self._request("GET", "/api/v1/datasets/")

    def create_dataset(self, name: str) -> CogneeResult:
        result = self._request("POST", "/api/v1/datasets/", json={"name": name})
        if result.ok:
            return result
        # Idempotent: dataset already owned by this tenant/user.
        reason = (result.reason or "").lower()
        if result.status_code in {400, 409, 422} and (
            "exist" in reason or "already" in reason or "duplicate" in reason
        ):
            return CogneeResult.success({"name": name, "existed": True})
        return result

    def add_text(self, dataset: str, text: str, *, filename: str) -> CogneeResult:
        files = {"data": (filename, text.encode("utf-8"), "text/markdown")}
        data = {"datasetName": dataset, "run_in_background": "false"}
        return self._request("POST", "/api/v1/add", data=data, files=files)

    def cognify(self, dataset: str, *, background: bool = False) -> CogneeResult:
        # Docs: datasets by name; runInBackground optional. Blocking until
        # graph is built is correct for plant SOPs (small). Background for bulk.
        return self._request(
            "POST",
            "/api/v1/cognify",
            json={"datasets": [dataset], "runInBackground": background},
            timeout=self.settings.cognify_timeout_s,
            retry=False,  # cognify is expensive; 402 must not retry
        )

    def search(
        self,
        dataset: str,
        query: str,
        *,
        top_k: int = 5,
        search_type: str = "GRAPH_COMPLETION",
    ) -> CogneeResult:
        return self._request(
            "POST",
            "/api/v1/search",
            json={
                "query": query,
                "datasets": [dataset],
                # Docs schema: searchType; snake_case alias also accepted.
                "search_type": search_type,
                "searchType": search_type,
                "only_context": True,
                "include_references": True,
                "top_k": top_k,
            },
        )
