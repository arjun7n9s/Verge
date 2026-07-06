"""Memory context routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from verge_memory import context_for_finding, query_memory

router = APIRouter(tags=["memory"])


class MemoryQueryBody(BaseModel):
    query: str = Field(min_length=1)
    findingId: str | None = None


@router.get("/findings/{finding_id}/context")
def finding_context(finding_id: str, request: Request) -> dict:
    """Incident/regulatory/plant context for a finding.

    Cognee outages or missing credentials are represented inside the response as
    `degraded: true`; a missing Verge finding is still a normal 404.
    """
    store = request.app.state.store
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")
    return context_for_finding(finding)


@router.post("/memory/query")
def memory_query(body: MemoryQueryBody, request: Request) -> dict:
    """Free-text query over incident/regulatory/plant memory."""
    finding = None
    if body.findingId:
        finding = request.app.state.store.get_finding(body.findingId)
        if finding is None:
            raise HTTPException(404, "finding not found")
    return query_memory(body.query, finding=finding)
