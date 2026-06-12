import os
from typing import Optional

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider

OPENAI_MODELS = ("gpt-4o-mini", "gpt-4o")
DEEPSEEK_MODELS = ("deepseek-chat", "deepseek-reasoner")
GEMINI_MODELS = ("gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash")


def is_local_provider_available() -> bool:
    try:
        import llama_cpp  # noqa: F401
        return True
    except ImportError:
        return False


def get_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    selected = (provider or os.getenv("DEFAULT_PROVIDER", "openai")).lower()
    selected_model = model or os.getenv("DEFAULT_MODEL", "gpt-4o")

    if selected == "openai":
        return OpenAIProvider(
            model_name=selected_model if selected_model in OPENAI_MODELS else "gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    if selected == "deepseek":
        from src.core.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider(
            model_name=selected_model if selected_model.startswith("deepseek") else "deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
        )
    if selected == "gemini":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            model_name=selected_model if selected_model.startswith("gemini-") else os.getenv("GEMINI_MODEL", GEMINI_MODELS[0]),
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    if selected == "ollama":
        from src.core.ollama_provider import OllamaProvider
        return OllamaProvider(
            model_name=selected_model if not selected_model.startswith("gpt") and not selected_model.startswith("deepseek") and not selected_model.startswith("gemini") else os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    if selected == "local":
        if not is_local_provider_available():
            raise ImportError("llama-cpp-python chưa cài. Xem requirements-local.txt.")
        from src.core.local_provider import LocalProvider
        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        )

    return OpenAIProvider(
        model_name=selected_model if selected_model in OPENAI_MODELS else "gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
