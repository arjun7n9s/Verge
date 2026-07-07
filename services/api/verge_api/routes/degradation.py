"""Operator degradation surface (spec §10.6)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..degradation import operator_banners

router = APIRouter(tags=["degradation"])


@router.get("/degradation")
def degradation_status(request: Request) -> dict:
    """Active operator banners derived from live platform posture."""
    s = request.app.state
    banners = operator_banners(
        store=s.store,
        llm=s.llm,
        vision=s.vision,
        readings=s.readings,
    )
    return {"banners": banners, "count": len(banners)}
