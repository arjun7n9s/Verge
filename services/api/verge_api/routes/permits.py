"""Permit-to-work routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from verge_schema.core import Permit

router = APIRouter(tags=["permits"])


class PermitsReplaceBody(BaseModel):
    permits: list[Permit]


@router.get("/permits")
def list_permits(request: Request) -> list[dict]:
    """Active open permits for the operator console / SIMOPS panel."""
    registry = request.app.state.permits
    return registry.as_dicts(now=datetime.now(UTC))


@router.get("/permits/conflicts")
def permit_conflicts(request: Request) -> dict:
    """SIMOPS conflicts among currently active permits."""
    registry = request.app.state.permits
    conflicts = registry.conflicts(now=datetime.now(UTC))
    return {"conflicts": conflicts, "count": len(conflicts)}


@router.put("/permits")
def replace_permits(body: PermitsReplaceBody, request: Request) -> dict:
    """Replace the active permit set (sim / edge-gateway feed)."""
    request.app.state.permits.replace(body.permits)
    return {"count": len(body.permits)}


@router.post("/permits/upsert")
def upsert_permit(permit: Permit, request: Request) -> dict:
    """Upsert one permit from the live event stream (risk-engine --post sync)."""
    request.app.state.permits.upsert(permit)
    return permit.model_dump(by_alias=True, mode="json")
