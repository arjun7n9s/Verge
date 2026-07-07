"""In-memory trace join index for plant-IT correlation (audit §9 observability).

Indexes recent pipeline stages keyed by ``traceId`` so ops can answer
"what happened on this edge reading path?" without mandating a full OTel
backend in dev. Production can still export spans to the collector separately.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class TraceSpan:
    trace_id: str
    stage: str
    ts: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "traceId": self.trace_id,
            "stage": self.stage,
            "ts": self.ts,
            "detail": self.detail,
        }


class TraceIndex:
    def __init__(self, *, max_entries: int = 4000) -> None:
        self._entries: deque[TraceSpan] = deque(maxlen=max_entries)
        self._by_trace: dict[str, deque[TraceSpan]] = {}
        self._max_per_trace = 64

    def record(
        self,
        trace_id: str | None,
        stage: str,
        *,
        detail: dict | None = None,
    ) -> None:
        if not trace_id:
            return
        span = TraceSpan(
            trace_id=trace_id,
            stage=stage,
            ts=datetime.now(UTC).isoformat(),
            detail=detail or {},
        )
        self._entries.append(span)
        bucket = self._by_trace.setdefault(trace_id, deque(maxlen=self._max_per_trace))
        bucket.append(span)

    def lookup(self, trace_id: str) -> list[dict]:
        spans = self._by_trace.get(trace_id)
        if spans is None:
            return []
        return [s.to_dict() for s in spans]

    def stats(self) -> dict:
        return {
            "indexedTraces": len(self._by_trace),
            "indexedSpans": len(self._entries),
        }
