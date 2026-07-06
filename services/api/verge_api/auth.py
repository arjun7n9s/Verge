"""Optional Keycloak OIDC bearer validation (disabled by default).

Set VERGE_AUTH_ENABLED=true with KEYCLOAK_URL + KEYCLOAK_REALM to require a
valid JWT on API routes. /health stays open for compose healthchecks.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

_OPEN_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def auth_enabled(env: dict[str, str] | None = None) -> bool:
    env = env or dict(os.environ)
    return env.get("VERGE_AUTH_ENABLED", "").lower() in {"1", "true", "yes"}


def _issuer(env: dict[str, str]) -> str:
    base = env.get("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
    realm = env.get("KEYCLOAK_REALM", "verge")
    return f"{base}/realms/{realm}"


def _jwks_url(env: dict[str, str]) -> str:
    return f"{_issuer(env)}/protocol/openid-connect/certs"


def decode_bearer(token: str, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env or dict(os.environ)
    try:
        import jwt
        from jwt import PyJWKClient
    except ImportError as exc:
        raise HTTPException(503, "auth dependencies not installed") from exc

    try:
        client = PyJWKClient(_jwks_url(env), cache_keys=True)
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=_issuer(env),
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(401, "invalid or expired token") from exc


class AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests when VERGE_AUTH_ENABLED=true."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not auth_enabled():
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in _OPEN_PATHS:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(401, "missing bearer token")
        decode_bearer(auth[7:].strip())
        return await call_next(request)
