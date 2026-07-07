"""Trace ID propagation middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .trace import TRACE_HEADER, current_trace_id, reset_trace_id, set_trace_id, trace_from_header


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = set_trace_id(trace_from_header(request.headers.get(TRACE_HEADER)))
        try:
            response = await call_next(request)
            tid = current_trace_id()
            if tid:
                response.headers[TRACE_HEADER] = tid
            return response
        finally:
            reset_trace_id(token)
