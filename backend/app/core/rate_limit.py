import time
from collections import defaultdict
from typing import Dict, List


class InMemoryRateLimiter:
    """
    Thread-safe rolling window rate limiter implemented in memory.
    Limits request frequency per client key (e.g. user ID or IP address).
    """

    def __init__(self, requests_limit: int = 10, window_seconds: int = 60):
        self.limit = requests_limit
        self.window = window_seconds
        self.history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        
        # Keep only timestamps that fall within the active window
        timestamps = [t for t in self.history[key] if t > cutoff]
        self.history[key] = timestamps

        if len(timestamps) >= self.limit:
            return False

        self.history[key].append(now)
        return True
