"""Rate limiting for the credential endpoints.

A small, dependency-free sliding-window counter. It is deliberately in-process:
the Compose stack runs a single API process, so a shared store would add an
operational dependency for no benefit. A multi-worker or multi-replica
deployment needs Redis or equivalent, because each process would otherwise keep
its own counters; docs/security.md records that limitation.

Only *failures* are counted, and a successful sign-in clears the counter, so a
legitimate user who mistypes a password once is not progressively locked out.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class FailureLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events.get(key)
        if events is None:
            return deque()
        cutoff = now - self.window
        while events and events[0] <= cutoff:
            events.popleft()
        if not events:
            self._events.pop(key, None)
            return deque()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until ``key`` may try again, or 0 when it is not blocked."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            if len(events) < self.limit:
                return 0
            return max(1, int(self.window - (now - events[0])) + 1)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            events.append(now)
            self._events[key] = events

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def reset(self) -> None:
        """Drop every counter. Used by tests and by an operator after a lockout."""
        with self._lock:
            self._events.clear()
