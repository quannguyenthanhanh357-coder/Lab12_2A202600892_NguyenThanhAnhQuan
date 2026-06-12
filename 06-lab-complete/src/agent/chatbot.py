from typing import Any, Dict

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ChatbotBaseline:
    """Simple LLM chatbot without tools — baseline for comparison."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def get_system_prompt(self) -> str:
        return (
            "You are a friendly movie recommendation assistant. "
            "Answer in Vietnamese when the user writes in Vietnamese. "
            "If the user asks about something outside movies, series, cinemas, "
            "streaming, or watch recommendations, politely say this demo only "
            "handles movie-related questions. Do not force unrelated requests "
            "into movie recommendations. "
            "You do NOT have access to external tools or a movie database — "
            "be honest when you are guessing from general knowledge."
        )

    def run(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("CHATBOT_START", {"input": user_input, "model": self.llm.model_name})
        result = self.llm.generate(user_input, system_prompt=self.get_system_prompt())
        logger.log_event(
            "CHATBOT_END",
            {"latency_ms": result.get("latency_ms"), "usage": result.get("usage")},
        )
        return {
            "answer": result["content"],
            "usage": result.get("usage"),
            "latency_ms": result.get("latency_ms"),
            "mode": "chatbot",
        }
