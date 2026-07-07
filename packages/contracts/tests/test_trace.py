"""Shared trace helper tests."""

from __future__ import annotations

from verge_contracts.trace import TRACE_HEADER, new_trace_id, resolve_trace_id, trace_from_header


def test_trace_from_header_accepts_or_mints() -> None:
    fixed = "abc12345deadbeef"
    assert trace_from_header(fixed) == fixed
    assert len(trace_from_header(None)) >= 16


def test_resolve_trace_id_prefers_header_then_event() -> None:
    event = {"traceId": "event-trace-12345678"}
    assert resolve_trace_id(header="header-trace-12345678", event=event) == "header-trace-12345678"
    assert resolve_trace_id(event=event) == "event-trace-12345678"
    minted = resolve_trace_id()
    assert len(minted) >= 16
    assert TRACE_HEADER == "X-Verge-Trace-Id"
    assert new_trace_id() != new_trace_id()
