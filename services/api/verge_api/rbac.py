"""Route-level RBAC when auth is enabled (audit §1).

Roles are read from standard Keycloak JWT claims. When auth is off (local dev),
all routes remain open.
"""

from __future__ import annotations

from fastapi import HTTPException

ROLE_VIEWER = frozenset({
    "verge-viewer", "verge-operator", "verge-supervisor", "verge-admin", "verge-service",
})
ROLE_OPERATOR = frozenset({"verge-operator", "verge-supervisor", "verge-admin", "verge-service"})
ROLE_ADMIN = frozenset({"verge-admin"})

_ADMIN_PREFIXES = (
    "/api/ops/backup",
    "/api/ops/audit/anchor",
    "/api/evidence/export",
)


def roles_from_claims(claims: dict) -> set[str]:
    roles: set[str] = set()
    realm = claims.get("realm_access") or {}
    roles.update(realm.get("roles") or [])
    for access in (claims.get("resource_access") or {}).values():
        if isinstance(access, dict):
            roles.update(access.get("roles") or [])
    extra = claims.get("roles")
    if isinstance(extra, list):
        roles.update(extra)
    return roles


def authorize(method: str, path: str, claims: dict) -> None:
    """Raise HTTP 403 when the token lacks permission for this route."""
    roles = roles_from_claims(claims)
    if method == "GET":
        if roles & ROLE_VIEWER:
            return
        raise HTTPException(403, "viewer role required")

    if any(path.startswith(p) for p in _ADMIN_PREFIXES):
        if roles & ROLE_ADMIN:
            return
        raise HTTPException(403, "admin role required")

    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        if roles & ROLE_OPERATOR:
            return
        raise HTTPException(403, "operator role required")
