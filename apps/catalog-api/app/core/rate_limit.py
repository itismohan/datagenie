"""Distributed API rate limiting for the catalog service.

The catalog must not rely on process-local counters because multiple API replicas
would otherwise create inconsistent limits. Redis is therefore the required store
when rate limiting is enabled outside local development.
"""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from time import time

import redis
from fastapi import Request


_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


class RateLimitStoreUnavailable(RuntimeError):
    """Raised when a required distributed rate-limit store cannot be used."""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RedisRateLimitStore:
    def __init__(self, redis_url: str) -> None:
        self.client = redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        try:
            count, ttl = self.client.eval(_RATE_LIMIT_SCRIPT, 1, key, window_seconds)
        except redis.RedisError as exc:
            raise RateLimitStoreUnavailable("Redis rate-limit store is unavailable.") from exc
        retry_after = max(1, int(ttl))
        return RateLimitResult(
            allowed=int(count) <= limit,
            limit=limit,
            remaining=max(0, limit - int(count)),
            retry_after_seconds=retry_after,
        )


@lru_cache
def get_rate_limit_store(redis_url: str) -> RedisRateLimitStore:
    return RedisRateLimitStore(redis_url)


def request_identity(request: Request) -> str:
    """Avoid storing a raw bearer credential in Redis while separating callers."""
    authorization = request.headers.get("Authorization")
    if authorization:
        return f"token:{sha256(authorization.encode('utf-8')).hexdigest()[:24]}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def rate_limit_key(request: Request, window_seconds: int) -> str:
    window = int(time() // window_seconds)
    return f"datagenie:catalog:rate-limit:{window}:{request_identity(request)}"
