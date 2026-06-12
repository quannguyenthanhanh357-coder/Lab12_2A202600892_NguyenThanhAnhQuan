"""Redis-backed monthly cost guard for LLM usage."""
import time
from functools import lru_cache

import redis
from fastapi import HTTPException

from app.config import settings


PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.00060


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def estimate_cost(input_tokens: int = 0, output_tokens: int = 0) -> float:
    return (
        (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
        + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    )


def _month_key(user_id: str) -> str:
    month = time.strftime("%Y-%m")
    return f"cost:{month}:{user_id}"


def get_monthly_cost(user_id: str) -> float:
    try:
        value = get_redis().get(_month_key(user_id))
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard storage unavailable") from exc
    return float(value or 0)


def check_budget(user_id: str, estimated_cost_usd: float = 0.0) -> None:
    used = get_monthly_cost(user_id)
    projected = used + estimated_cost_usd
    if projected > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(used, 6),
                "projected_usd": round(projected, 6),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "first day of next month UTC",
            },
        )


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> dict:
    cost = estimate_cost(input_tokens, output_tokens)
    key = _month_key(user_id)
    try:
        client = get_redis()
        total = client.incrbyfloat(key, cost)
        client.expire(key, 60 * 60 * 24 * 45)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard storage unavailable") from exc

    return {
        "user_id": user_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "monthly_total_usd": round(float(total), 6),
        "monthly_budget_usd": settings.monthly_budget_usd,
    }
