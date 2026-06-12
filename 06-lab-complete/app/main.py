"""Production-ready AI agent for Day 12 deployment lab."""
import json
import logging
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_cost, get_monthly_cost, record_usage
from app.rate_limiter import check_rate_limit, get_redis, redis_ping
from utils.mock_llm import ask as llm_ask


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0


def log_event(event: str, **fields) -> None:
    payload = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logger.info(json.dumps(payload, separators=(",", ":")))


def _token_count(text: str) -> int:
    return max(1, len(text.split()) * 2)


def _history_key(user_id: str) -> str:
    safe_user_id = "".join(ch if ch.isalnum() or ch in "-_:@" else "_" for ch in user_id)
    return f"history:{safe_user_id}"


def load_history(user_id: str) -> list[dict]:
    try:
        rows = get_redis().lrange(_history_key(user_id), 0, -1)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Conversation storage unavailable") from exc
    return [json.loads(row) for row in rows]


def append_history(user_id: str, role: str, content: str) -> None:
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    key = _history_key(user_id)
    try:
        client = get_redis()
        pipe = client.pipeline()
        pipe.rpush(key, json.dumps(message, separators=(",", ":")))
        pipe.ltrim(key, -20, -1)
        pipe.expire(key, settings.history_ttl_seconds)
        pipe.execute()
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Conversation storage unavailable") from exc


def last_user_message(history: list[dict]) -> str | None:
    for message in reversed(history):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    log_event(
        "startup",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    _is_ready = redis_ping()
    if _is_ready:
        log_event("ready", redis=True)
    else:
        log_event("not_ready", redis=False)

    yield

    _is_ready = False
    log_event("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    started = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
    except Exception:
        _error_count += 1
        log_event("request_error", method=request.method, path=request.url.path)
        raise

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    duration_ms = round((time.time() - started) * 1000, 1)
    log_event(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field("default", min_length=1, max_length=80)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    turn: int
    cost: dict
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics (requires X-API-Key)",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    api_key_id: str = Depends(verify_api_key),
):
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Agent is not ready")

    user_bucket = f"{api_key_id}:{body.user_id}"
    check_rate_limit(user_bucket)

    history = load_history(user_bucket)
    input_tokens = _token_count(body.question)
    check_budget(user_bucket, estimate_cost(input_tokens=input_tokens))

    normalized_question = body.question.strip().lower()
    previous_message = last_user_message(history)
    append_history(user_bucket, "user", body.question)

    if previous_message and "what did i just say" in normalized_question:
        answer = f'Your previous message was: "{previous_message}"'
    else:
        answer = llm_ask(body.question)

    output_tokens = _token_count(answer)
    check_budget(
        user_bucket,
        estimate_cost(input_tokens=input_tokens, output_tokens=output_tokens),
    )
    append_history(user_bucket, "assistant", answer)
    usage = record_usage(user_bucket, input_tokens, output_tokens)

    log_event(
        "agent_call",
        user_id=body.user_id,
        api_key_id=api_key_id,
        client=str(request.client.host) if request.client else "unknown",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    user_turns = len([message for message in history if message.get("role") == "user"]) + 1
    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        turn=user_turns,
        cost=usage,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {
            "llm": "mock" if not settings.openai_api_key else settings.llm_model,
            "redis": redis_ping(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Startup checks have not passed")
    if not redis_ping():
        raise HTTPException(status_code=503, detail="Redis is not available")
    return {"ready": True, "redis": True}


@app.get("/metrics", tags=["Operations"])
def metrics(api_key_id: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "monthly_budget_usd": settings.monthly_budget_usd,
        "current_key_monthly_cost_usd": round(get_monthly_cost(api_key_id), 6),
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }


def _handle_signal(signum, _frame):
    global _is_ready
    _is_ready = False
    log_event("signal", signum=signum)


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    log_event("serve", host=settings.host, port=settings.port)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
