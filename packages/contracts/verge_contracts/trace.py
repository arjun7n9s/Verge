"""Shared trace identifiers for edge → bus → API → audit correlation (spec §7)."""

from __future__ import annotations

import uuid

TRACE_HEADER = "X-Verge-Trace-Id"


def new_trace_id() -> str:
    return uuid.uuid4().hex


def trace_from_header(header_value: str | None) -> str:
    if header_value and len(header_value.strip()) >= 8:
        return header_value.strip()
    return new_trace_id()


def resolve_trace_id(
    *,
    header: str | None = None,
    event: dict | None = None,
) -> str:
    """Pick a trace id from HTTP header, event envelope, or mint a new one."""
    if header and len(header.strip()) >= 8:
        return header.strip()
    if event:
        existing = event.get("traceId")
        if existing and len(str(existing)) >= 8:
            return str(existing)
    return new_trace_id()
