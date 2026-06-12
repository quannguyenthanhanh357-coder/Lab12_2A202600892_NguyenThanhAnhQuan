import time
from typing import Any, Dict, Generator, List, Optional

import requests

from src.core.llm_provider import LLMProvider

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def list_available_models(
    api_key: Optional[str] = None,
    base_url: str = GEMINI_API_BASE_URL,
) -> List[str]:
    """Return Gemini text models that support generateContent."""
    if not api_key:
        return []

    try:
        resp = requests.get(f"{base_url}/models", params={"key": api_key}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    models: List[str] = []
    skip_terms = ("embedding", "imagen", "veo", "tts", "live", "image", "banana")
    for item in data.get("models", []):
        name = item.get("name", "").removeprefix("models/")
        methods = item.get("supportedGenerationMethods", [])
        lowered = name.lower()
        if (
            name.startswith("gemini-")
            and "generateContent" in methods
            and not any(term in lowered for term in skip_terms)
        ):
            models.append(name)

    return models


class GeminiProvider(LLMProvider):
    """LLM provider for the Gemini API using direct REST calls."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash-lite",
        api_key: Optional[str] = None,
        base_url: str = GEMINI_API_BASE_URL,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ):
        super().__init__(model_name=model_name, api_key=api_key)
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY in .env")

        start_time = time.time()
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        resp = requests.post(
            f"{self.base_url}/models/{self.model_name}:generateContent",
            params={"key": self.api_key},
            json=payload,
            timeout=180,
        )
        if not resp.ok:
            try:
                message = resp.json().get("error", {}).get("message", resp.text)
            except ValueError:
                message = resp.text
            raise RuntimeError(f"Gemini API error {resp.status_code}: {message}")

        data = resp.json()
        latency_ms = int((time.time() - start_time) * 1000)

        parts = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        content = "".join(part.get("text", "") for part in parts).strip()
        usage_raw = data.get("usageMetadata", {})
        usage = {
            "prompt_tokens": usage_raw.get("promptTokenCount", 0),
            "completion_tokens": usage_raw.get("candidatesTokenCount", 0),
            "total_tokens": usage_raw.get("totalTokenCount", 0),
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "gemini",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt=system_prompt)["content"]
