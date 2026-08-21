from collections import deque
from threading import Lock
from time import monotonic


class RateLimitExceeded(RuntimeError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("MCP rate limit exceeded.")


class SlidingWindowRateLimiter:
    """Process-local limiter for the single internal beta instance.

    Production scale-out must replace this with a shared Redis-backed store before
    allowing more than the approved internal tenant/host combination.
    """

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= now - self.window_seconds:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])) + 1)
                raise RateLimitExceeded(retry_after)
            events.append(now)
