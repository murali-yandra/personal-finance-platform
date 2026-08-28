"""In-process request rate limiting.

``10-security_standards.md`` section 7 recommends 100 requests per minute per
user. This is a fixed-window counter held in memory, which is correct for the
single-container MVP; a multi-container deployment needs a shared store such as
Redis, and the limiter is written so that swap is a change of backend rather
than of call sites.
"""

import threading
import time
from dataclasses import dataclass

DEFAULT_LIMIT = 100
DEFAULT_WINDOW_SECONDS = 60

# A bound on tracked keys, so an unauthenticated flood from many addresses
# cannot grow the counter map without limit.
MAX_TRACKED_KEYS = 10_000


@dataclass(frozen=True)
class RateLimitDecision:
    """The outcome of one rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimiter:
    """Fixed-window request counter, keyed by caller."""

    def __init__(
        self,
        limit: int = DEFAULT_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        clock=time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = {}

    def check(self, key: str) -> RateLimitDecision:
        """Count one request against a key and decide whether to allow it."""
        now = self._clock()
        with self._lock:
            window_start, count = self._windows.get(key, (now, 0))

            if now - window_start >= self._window:
                window_start, count = now, 0

            count += 1
            self._windows[key] = (window_start, count)

            if len(self._windows) > MAX_TRACKED_KEYS:
                self._evict_expired(now)

        elapsed = now - window_start
        retry_after = max(1, int(self._window - elapsed))
        return RateLimitDecision(
            allowed=count <= self._limit,
            limit=self._limit,
            remaining=max(0, self._limit - count),
            retry_after_seconds=retry_after,
        )

    def reset(self, key: str | None = None) -> None:
        """Clear counters, for one key or all of them."""
        with self._lock:
            if key is None:
                self._windows.clear()
            else:
                self._windows.pop(key, None)

    def _evict_expired(self, now: float) -> None:
        """Drop windows that have already elapsed. Caller holds the lock."""
        expired = [
            key
            for key, (start, _) in self._windows.items()
            if now - start >= self._window
        ]
        for key in expired:
            del self._windows[key]
