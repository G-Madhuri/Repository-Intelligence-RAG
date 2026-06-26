import time
from typing import Dict, Any, Optional

class CacheEntry:
    def __init__(self, value: Any, ttl: Optional[float] = None):
        self.value = value
        self.expires_at = time.time() + ttl if ttl is not None else None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

class MemoryCache:
    """
    In-memory cache with TTL support for accelerating AI agent executions
    and caching heavy search/graph query results.
    """
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        if entry.is_expired():
            del self._cache[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        self._cache.clear()

# Global memory cache singleton
memory_cache = MemoryCache()
