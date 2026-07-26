import time
import json
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict
import redis
from config import settings

logger = logging.getLogger(__name__)

class LRUCache:
    """Thread-safe in-memory LRU cache fallback."""
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        item = self.cache[key]
        if item["expires_at"] and time.time() > item["expires_at"]:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return item["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expires_at = time.time() + ttl if ttl else None
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = {"value": value, "expires_at": expires_at}
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

class CacheManager:
    """Unified cache manager reading Upstash Redis first with in-memory LRU fallback."""
    def __init__(self):
        self.lru = LRUCache(capacity=2000)
        self.redis_client = None
        
        if settings.UPSTASH_REDIS_URL and settings.UPSTASH_REDIS_TOKEN:
            try:
                # Format url for redis-py
                redis_url = settings.UPSTASH_REDIS_URL
                if not redis_url.startswith("redis://") and not redis_url.startswith("rediss://"):
                    redis_url = f"rediss://:{settings.UPSTASH_REDIS_TOKEN}@{redis_url.replace('https://', '')}:6379"
                
                self.redis_client = redis.Redis.from_url(redis_url, socket_timeout=3.0)
                logger.info("Connected to Upstash Redis cache shield.")
            except Exception as e:
                logger.warning(f"Could not connect to Redis ({e}). Falling back to in-memory LRU cache.")
                self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        # Try Redis first
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.warning(f"Redis read error ({e}). Checking LRU fallback.")

        # Fallback to local LRU
        return self.lru.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = 900):
        # Write to local LRU
        self.lru.set(key, value, ttl=ttl)

        # Write to Redis if available
        if self.redis_client:
            try:
                serialized = json.dumps(value, default=str)
                if ttl:
                    self.redis_client.setex(key, ttl, serialized)
                else:
                    self.redis_client.set(key, serialized)
            except Exception as e:
                logger.warning(f"Redis write error ({e}). Saved in local LRU.")

    def set_permanent(self, key: str, value: Any):
        """Used for historical data (TTL = infinite)."""
        self.set(key, value, ttl=None)

cache_manager = CacheManager()
