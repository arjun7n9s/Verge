"""Distributed trace context (OpenTelemetry-inspired, spec §7).

Propagates ``X-Verge-Trace-Id`` across API → risk-engine → audit payloads so
plant IT can correlate edge → bus → engine → console without mandating a full
OTel collector in dev.
"""

from __future__ import annotations

import contextvars
import uuid

TRACE_HEADER = "X-Verge-Trace-Id"
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def current_trace_id() -> str | None:
    return _trace_id.get()


def set_trace_id(trace_id: str | None) -> contextvars.Token:
    return _trace_id.set(trace_id)


def reset_trace_id(token: contextvars.Token) -> None:
    _trace_id.reset(token)


def new_trace_id() -> str:
    return uuid.uuid4().hex


def trace_from_header(header_value: str | None) -> str:
    if header_value and len(header_value) >= 8:
        return header_value.strip()
    return new_trace_id()
