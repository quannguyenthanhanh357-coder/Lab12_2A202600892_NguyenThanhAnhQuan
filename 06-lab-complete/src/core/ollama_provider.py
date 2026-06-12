"""
LLM Provider cho Ollama — chạy model local qua REST API.
Không cần API key, cần Ollama server đang chạy tại localhost:11434.
"""
import json
import time
import requests
from typing import Dict, Any, Optional, Generator, List

from src.core.llm_provider import LLMProvider

OLLAMA_BASE_URL = "http://localhost:11434"


def list_available_models(base_url: str = OLLAMA_BASE_URL) -> List[str]:
    """Trả về danh sách model đang có trong Ollama. Rỗng nếu server chưa chạy."""
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def is_ollama_running(base_url: str = OLLAMA_BASE_URL) -> bool:
    """Kiểm tra Ollama server có đang chạy không."""
    try:
        requests.get(f"{base_url}/api/tags", timeout=2)
        return True
    except Exception:
        return False


class OllamaProvider(LLMProvider):
    """
    LLM Provider cho Ollama — gọi REST API tại localhost:11434.
    Hỗ trợ mọi model Ollama đã pull (llama3, mistral, qwen2, ...).
    Tối ưu với temperature thấp để gọi tool chính xác hơn.
    """

    is_local_model = True  # báo hiệu cho agent dùng compact prompt

    def __init__(
        self,
        model_name: str = "llama3",
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = 0.1,
        num_predict: int = 512,
    ):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.num_predict = num_predict

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "stop": ["Observation:", "<|end|>", "<|im_end|>", "Human:", "User:"],
                "num_predict": self.num_predict,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Không thể kết nối Ollama tại {self.base_url}. "
                "Hãy chạy: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Ollama timeout sau 180s. Model '{self.model_name}' có thể quá lớn cho máy."
            )

        data = resp.json()
        latency_ms = int((time.time() - start_time) * 1000)
        content = data.get("response", "").strip()

        p_tokens = data.get("prompt_eval_count", 0)
        c_tokens = data.get("eval_count", 0)
        usage = {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": p_tokens + c_tokens,
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "ollama",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": self.temperature, "num_predict": self.num_predict},
        }
        if system_prompt:
            payload["system"] = system_prompt

        with requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=True,
            timeout=180,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
