"""Store-and-forward buffer (P7, §10.6 'stream bus lag' row).

A network blip between the OT edge and the central bus must never drop safety
data. Events are buffered locally and flushed on reconnect; the buffer is
bounded (oldest-dropped with a counter) so a long outage can't exhaust memory —
and the drop count is surfaced, never silent.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable


class StoreAndForward:
    def __init__(self, maxlen: int = 100_000) -> None:
        self._q: deque[dict] = deque(maxlen=maxlen)
        self.dropped = 0
        self._online = True

    @property
    def online(self) -> bool:
        return self._online

    @property
    def buffered(self) -> int:
        return len(self._q)

    def go_offline(self) -> None:
        self._online = False

    def submit(self, event: dict, sink: Callable[[dict], None]) -> None:
        """Send now if online, else buffer. Bounded buffer drops oldest + counts."""
        if self._online:
            sink(event)
            return
        if len(self._q) == self._q.maxlen:
            self.dropped += 1
        self._q.append(event)

    def reconnect(self, sink: Callable[[dict], None]) -> int:
        """Flush the buffer in order; return how many were forwarded."""
        self._online = True
        n = 0
        while self._q:
            sink(self._q.popleft())
            n += 1
        return n
