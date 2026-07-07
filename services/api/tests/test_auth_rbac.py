"""Auth + RBAC tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from verge_api.auth import auth_enabled, decode_bearer
from verge_api.rbac import authorize, roles_from_claims


def test_roles_from_claims_merges_realm_and_resource() -> None:
    claims = {
        "realm_access": {"roles": ["verge-viewer"]},
        "resource_access": {"verge-console": {"roles": ["verge-operator"]}},
    }
    assert roles_from_claims(claims) == {"verge-viewer", "verge-operator"}


def test_authorize_get_requires_viewer_role() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize("GET", "/api/findings", {"realm_access": {"roles": ["other"]}})
    assert exc.value.status_code == 403


def test_authorize_post_allows_operator() -> None:
    authorize(
        "POST",
        "/api/findings/F-1/transition",
        {"realm_access": {"roles": ["verge-operator"]}},
    )


def test_authorize_admin_backup_route() -> None:
    with pytest.raises(HTTPException):
        authorize(
            "POST",
            "/api/ops/backup/export",
            {"realm_access": {"roles": ["verge-operator"]}},
        )
    authorize(
        "POST",
        "/api/ops/backup/export",
        {"realm_access": {"roles": ["verge-admin"]}},
    )


def test_authorize_admin_audit_anchor_post() -> None:
    with pytest.raises(HTTPException):
        authorize(
            "POST",
            "/api/ops/audit/anchor",
            {"realm_access": {"roles": ["verge-operator"]}},
        )
    authorize(
        "POST",
        "/api/ops/audit/anchor",
        {"realm_access": {"roles": ["verge-admin"]}},
    )


def test_decode_bearer_rejects_without_jwks(monkeypatch) -> None:
    monkeypatch.setenv("VERGE_AUTH_ENABLED", "true")
    monkeypatch.setenv("KEYCLOAK_URL", "http://invalid.local")
    with pytest.raises(HTTPException) as exc:
        decode_bearer("not.a.jwt")
    assert exc.value.status_code in {401, 503}


def test_auth_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("VERGE_AUTH_ENABLED", raising=False)
    assert auth_enabled() is False
