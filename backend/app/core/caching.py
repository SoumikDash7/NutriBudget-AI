import time
from typing import Any, Dict, Tuple, Optional


class InMemoryTTLCache:
    """
    Lightweight, thread-safe (in FastAPI's single-threaded event loop),
    in-memory key-value cache with Time-To-Live (TTL) expiration support.
    """

    def __init__(self, default_ttl_seconds: int = 86400):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        value, expire_time = self.cache[key]
        if time.time() > expire_time:
            del self.cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expire_time = time.time() + ttl
        self.cache[key] = (value, expire_time)

    def clear(self) -> None:
        self.cache.clear()
