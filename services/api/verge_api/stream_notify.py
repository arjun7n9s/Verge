"""Helpers to push SSE updates after API mutations via the transactional outbox."""

from __future__ import annotations

from fastapi import FastAPI

from .outbox import FINDING_TRANSITION, FINDINGS_UPDATED, READING_INGESTED
from .redpanda_publish import maybe_publish_event


def _reading_event(payload: dict) -> dict:
    return payload.get("event") or payload


def _publish_outbox_event(app: FastAPI, kind: str, payload: dict) -> None:
    bus = getattr(app.state, "stream_bus", None)
    if kind in (FINDINGS_UPDATED, FINDING_TRANSITION):
        if bus is not None:
            store = app.state.store
            findings = [f.model_dump(by_alias=True, mode="json") for f in store.list_findings()]
            bus.publish_findings(findings)
        return
    if kind == READING_INGESTED:
        event = _reading_event(payload)
        if bus is not None:
            bus.publish_event(event)
        if not payload.get("skipRedpanda"):
            maybe_publish_event(event)


def notify_findings(app: FastAPI) -> None:
    """Legacy direct notify — prefer ``drain_outbox`` after durable writes."""
    bus = getattr(app.state, "stream_bus", None)
    if bus is None:
        return
    store = app.state.store
    findings = [f.model_dump(by_alias=True, mode="json") for f in store.list_findings()]
    bus.publish_findings(findings)


def notify_reading(app: FastAPI, event: dict) -> None:
    """Legacy direct notify — prefer ``enqueue_reading`` + ``drain_outbox``."""
    bus = getattr(app.state, "stream_bus", None)
    if bus is not None:
        bus.publish_event(event)
    maybe_publish_event(event)


def drain_outbox(app: FastAPI, *, limit: int = 100) -> int:
    """Publish pending outbox rows and return how many were drained."""
    store = app.state.store

    def publish(kind: str, payload: dict) -> None:
        _publish_outbox_event(app, kind, payload)

    if hasattr(store, "drain_outbox"):
        return store.drain_outbox(publish, limit=limit)
    notify_findings(app)
    return 0
