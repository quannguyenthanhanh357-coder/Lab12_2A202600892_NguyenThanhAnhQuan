"""Deterministic scope guard for the movie recommendation demo.

The agent is intentionally fail-closed: if a prompt is not clearly about
movies, series, cinemas, streaming, or watch recommendations, it does not call
an LLM. This prevents small/local models from forcing off-topic prompts into
movie-shaped hallucinations.
"""

import re
import unicodedata
from typing import Any, Dict

MOVIE_INTENT_TERMS = (
    "phim",
    "movie",
    "film",
    "series",
    "serial",
    "cinema",
    "tmdb",
    "imdb",
    "netflix",
    "disney",
    "prime video",
    "hbo",
    "max",
    "trailer",
    "dien vien",
    "dao dien",
    "the loai",
    "rating",
    "review",
    "rap",
    "xem phim",
    "xem gi",
    "watch",
    "streaming",
    "recommend",
    "recommendation",
    "goi y phim",
    "de xuat phim",
    "tim phim",
    "so sanh phim",
    "trending",
)

KNOWN_MOVIE_TITLES = (
    "inception",
    "interstellar",
    "the prestige",
    "get out",
    "parasite",
    "oppenheimer",
    "barbie",
    "avatar",
    "titanic",
)


def _normalize(text: str) -> str:
    text = text.strip().lower()
    decomposed = unicodedata.normalize("NFD", text)
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", no_accents)


def has_movie_intent(query: str) -> bool:
    """Return True when the user clearly asks about movies or watching."""
    normalized = _normalize(query)
    if not normalized:
        return False

    if any(term in normalized for term in MOVIE_INTENT_TERMS):
        return True

    return any(title in normalized for title in KNOWN_MOVIE_TITLES)


def is_clear_off_topic(query: str) -> bool:
    """Fail closed: any non-empty prompt without movie intent is out of scope."""
    return bool(query.strip()) and not has_movie_intent(query)


def build_off_topic_result(query: str) -> Dict[str, Any]:
    """Return a deterministic response instead of calling LLMs/tools."""
    return {
        "answer": (
            "Mình là demo gợi ý phim nên mình sẽ không trả lời câu ngoài phạm vi phim "
            f"như `{query}` để tránh ảo giác.\n\n"
            "Bạn có thể viết lại theo hướng phim, ví dụ:\n"
            "- Hôm nay đi đâu xem phim thì hợp?\n"
            "- Gợi ý phim để xem khi đang muốn ra ngoài thư giãn.\n"
            "- Tối nay xem phim hài gia đình nào ổn?\n"
            "- Tìm phim giống Inception."
        ),
        "trace": [],
        "steps": 0,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "latency_ms": 0,
        "mode": "domain_guard",
    }
