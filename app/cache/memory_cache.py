from cachetools import TTLCache
from typing import Any
from app.config import get_settings

SET = get_settings()

# Simple in-memory TTL cache. For Redis, replace with aioredis operations.
cache = TTLCache(maxsize=4096, ttl=SET.CACHE_TTL_SECONDS)


def cache_get(key: str) -> Any | None:
    return cache.get(key)


def cache_set(key: str, value: Any):
    cache[key] = value
