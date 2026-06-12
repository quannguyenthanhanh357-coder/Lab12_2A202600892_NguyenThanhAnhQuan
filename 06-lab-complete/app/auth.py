"""API key authentication."""
import hashlib
import hmac

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def api_key_fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or not hmac.compare_digest(api_key, settings.agent_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key.",
        )
    return api_key_fingerprint(api_key)
