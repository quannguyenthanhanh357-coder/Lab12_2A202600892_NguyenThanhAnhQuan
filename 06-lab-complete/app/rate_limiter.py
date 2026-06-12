"""Redis-backed sliding-window rate limiter."""
import time
from functools import lru_cache

import redis
from fastapi import HTTPException

from app.config import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def redis_ping() -> bool:
    try:
        return bool(get_redis().ping())
    except redis.RedisError:
        return False


def check_rate_limit(user_id: str) -> dict:
    now_ms = int(time.time() * 1000)
    window_ms = settings.rate_limit_window_seconds * 1000
    key = f"rate:{user_id}"

    try:
        client = get_redis()
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)
        pipe.zcard(key)
        _, current_count = pipe.execute()

        if current_count >= settings.rate_limit_per_minute:
            oldest = client.zrange(key, 0, 0, withscores=True)
            retry_after = settings.rate_limit_window_seconds
            if oldest:
                retry_after = max(1, int((oldest[0][1] + window_ms - now_ms) / 1000) + 1)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": settings.rate_limit_per_minute,
                    "window_seconds": settings.rate_limit_window_seconds,
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        member = f"{now_ms}:{time.perf_counter_ns()}"
        pipe = client.pipeline()
        pipe.zadd(key, {member: now_ms})
        pipe.expire(key, settings.rate_limit_window_seconds * 2)
        pipe.execute()
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Rate limiter storage unavailable") from exc

    remaining = settings.rate_limit_per_minute - current_count - 1
    return {"limit": settings.rate_limit_per_minute, "remaining": remaining}
