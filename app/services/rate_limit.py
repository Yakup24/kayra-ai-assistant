from __future__ import annotations

from collections import defaultdict, deque
from time import time
from threading import Lock


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time()
        window_start = now - window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= window_start:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                return False, retry_after
            hits.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
