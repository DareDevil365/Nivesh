"""Bounded local cache, optionally backed by standard Redis or Upstash REST."""

import copy
import json
import logging
import threading
import time
from collections import OrderedDict

import httpx
import redis

from config import settings

logger = logging.getLogger(__name__)


class LRUCache:
    def __init__(self, capacity=2000):
        self.capacity = capacity
        self.cache = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self.cache.get(key)
            if item is None:
                return None
            expires, value = item
            if expires is not None and time.monotonic() >= expires:
                del self.cache[key]
                return None
            self.cache.move_to_end(key)
            return copy.deepcopy(value)

    def set(self, key, value, ttl=None):
        with self._lock:
            self.cache[key] = (
                time.monotonic() + ttl if ttl is not None else None,
                copy.deepcopy(value),
            )
            self.cache.move_to_end(key)
            while len(self.cache) > self.capacity:
                self.cache.popitem(last=False)


class CacheManager:
    def __init__(self):
        self.lru = LRUCache()
        self.redis_client = None
        self.rest_url = None
        self.rest_token = None
        self.retry_after = 0.0
        if settings.REDIS_URL or settings.UPSTASH_REDIS_URL.startswith(("redis://", "rediss://")):
            try:
                self.redis_client = redis.Redis.from_url(
                    settings.REDIS_URL or settings.UPSTASH_REDIS_URL,
                    socket_timeout=0.8,
                    socket_connect_timeout=0.8,
                )
            except Exception:
                logger.warning("Redis configuration invalid; using local cache.")
        elif settings.UPSTASH_REDIS_URL and settings.UPSTASH_REDIS_TOKEN:
            self.rest_url = settings.UPSTASH_REDIS_URL.rstrip("/")
            self.rest_token = settings.UPSTASH_REDIS_TOKEN

    def command(self, *args):
        if self.rest_url:
            response = httpx.post(
                self.rest_url,
                headers={"Authorization": f"Bearer {self.rest_token}"},
                json=list(args),
                timeout=1,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise ValueError("Cache command failed")
            return payload.get("result")
        if self.redis_client:
            return self.redis_client.execute_command(*args)
        return None

    def get(self, key):
        local = self.lru.get(key)
        if local is not None:
            return local
        if time.monotonic() < self.retry_after:
            return None
        try:
            value = self.command("GET", key)
            # Do not extend a remote TTL in local memory; only the writer sets local TTL.
            return json.loads(value) if value is not None else None
        except Exception:
            self.retry_after = time.monotonic() + 60
            logger.warning("Shared cache unavailable; using local cache for 60 seconds.")
            return None

    def set(self, key, value, ttl=900):
        self.lru.set(key, value, ttl)
        if time.monotonic() < self.retry_after:
            return
        try:
            serialized = json.dumps(value, allow_nan=False)
            if ttl is not None:
                if ttl <= 0:
                    return
                self.command("SET", key, serialized, "EX", int(ttl))
            else:
                self.command("SET", key, serialized)
        except Exception:
            self.retry_after = time.monotonic() + 60

    def set_permanent(self, key, value):
        self.set(key, value, ttl=None)


cache_manager = CacheManager()
