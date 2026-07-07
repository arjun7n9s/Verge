"""Helpers to push SSE updates after API mutations."""

from __future__ import annotations

from fastapi import FastAPI


def notify_findings(app: FastAPI) -> None:
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
