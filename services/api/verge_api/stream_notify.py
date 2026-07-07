"""Helpers to push SSE updates after API mutations via the transactional outbox."""

from __future__ import annotations

from fastapi import FastAPI

from .outbox import FINDINGS_UPDATED, READING_INGESTED


def _publish_outbox_event(app: FastAPI, kind: str, payload: dict) -> None:
    bus = getattr(app.state, "stream_bus", None)
    if bus is None:
        return
    if kind in (FINDINGS_UPDATED, "finding-transition"):
        store = app.state.store
        findings = [f.model_dump(by_alias=True, mode="json") for f in store.list_findings()]
        bus.publish_findings(findings)
    elif kind == READING_INGESTED:
        bus.publish_event(payload)


def notify_findings(app: FastAPI) -> None:
    """Legacy direct notify — prefer ``drain_outbox`` after durable writes."""
    bus = getattr(app.state, "stream_bus", None)
    if bus is None:
        return
    store = app.state.store
    findings = [f.model_dump(by_alias=True, mode="json") for f in store.list_findings()]
    bus.publish_findings(findings)


def notify_reading(app: FastAPI, event: dict) -> None:
    bus = getattr(app.state, "stream_bus", None)
    if bus is None:
        return
    bus.publish_event(event)


def drain_outbox(app: FastAPI, *, limit: int = 100) -> int:
    """Publish pending outbox rows and return how many were drained."""
    store = app.state.store

    def publish(kind: str, payload: dict) -> None:
        _publish_outbox_event(app, kind, payload)

    if hasattr(store, "drain_outbox"):
        return store.drain_outbox(publish, limit=limit)
    notify_findings(app)
    return 0
