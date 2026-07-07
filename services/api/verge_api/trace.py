"""Distributed trace context (OpenTelemetry-inspired, spec §7).

Propagates ``X-Verge-Trace-Id`` across API → risk-engine → audit payloads so
plant IT can correlate edge → bus → engine → console without mandating a full
OTel collector in dev.
"""

from __future__ import annotations

import contextvars

from verge_contracts.trace import TRACE_HEADER, new_trace_id, trace_from_header

__all__ = [
    "TRACE_HEADER",
    "current_trace_id",
    "new_trace_id",
    "payload_with_trace",
    "record_trace",
    "reset_trace_id",
    "set_trace_id",
    "trace_from_header",
]

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def current_trace_id() -> str | None:
    return _trace_id.get()


def set_trace_id(trace_id: str | None) -> contextvars.Token:
    return _trace_id.set(trace_id)


def reset_trace_id(token: contextvars.Token) -> None:
    _trace_id.reset(token)


def payload_with_trace(payload: dict, *, trace_id: str | None = None) -> dict:
    tid = trace_id or current_trace_id()
    if not tid:
        return payload
    out = dict(payload)
    out.setdefault("traceId", tid)
    return out


def record_trace(app, trace_id: str | None, stage: str, **detail) -> None:
    index = getattr(getattr(app, "state", None), "trace_index", None)
    if index is None:
        return
    index.record(trace_id, stage, detail=detail)
