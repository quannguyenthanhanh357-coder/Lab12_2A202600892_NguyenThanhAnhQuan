"""
Streamlit demo: Chatbot vs ReAct Movie Recommendation Agent.

Run from project root:
    streamlit run src/app.py
"""
import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.agent.chatbot import ChatbotBaseline
from src.core.domain_guard import build_off_topic_result, is_clear_off_topic
from src.core.factory import get_llm_provider
from src.tools.registry import TOOL_SPECS
from src.ui.comparison import (
    build_model_options,
    render_comparison_result,
    render_metrics_table,
    run_parallel_comparison,
)

st.set_page_config(page_title="Movie ReAct Agent Demo", page_icon="🎬", layout="wide")

EXAMPLE_PROMPTS = [
    "Tôi vừa xem Inception, gợi ý phim tương tự có trên Netflix.",
    "Phim trending tuần này ở VN thể loại Sci-Fi là gì?",
    "Tôi buồn, muốn xem phim nhẹ nhàng — gợi ý 3 phim.",
    "So sánh Inception, Interstellar và The Prestige.",
    "Phim Get Out có trên Netflix VN không?",
]


def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_trace" not in st.session_state:
        st.session_state.last_trace = None
    if "last_metrics" not in st.session_state:
        st.session_state.last_metrics = None
    if "cmp_query" not in st.session_state:
        st.session_state.cmp_query = ""
    if "cmp_results" not in st.session_state:
        st.session_state.cmp_results = None


def extract_movies_from_trace(trace):
    """Extract movie data with images from trace observations."""
    movies = []
    seen_ids = set()
    if not trace:
        return movies
    for step in trace:
        obs_raw = step.get("observation")
        if not obs_raw:
            continue
        try:
            obs = json.loads(obs_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        # Single movie detail
        if obs.get("poster_url") and obs.get("id") not in seen_ids:
            movies.append(obs)
            seen_ids.add(obs["id"])
        # List of movies (search, similar, trending, mood, compare)
        for key in ("movies", "comparison"):
            for m in obs.get(key, []):
                if isinstance(m, dict) and m.get("poster_url") and m.get("id") not in seen_ids:
                    movies.append(m)
                    seen_ids.add(m["id"])
    return movies


def render_movie_cards(movies, max_cols=4):
    """Render movie poster cards in a grid."""
    if not movies:
        return
    st.markdown("---")
    st.markdown("🎬 **Phim liên quan:**")
    cols = st.columns(min(len(movies), max_cols))
    for idx, movie in enumerate(movies[:max_cols * 2]):
        col = cols[idx % max_cols]
        with col:
            poster = movie.get("poster_url")
            if poster:
                st.image(poster, use_container_width=True)
            title = movie.get("title", "")
            year = movie.get("year", "")
            rating = movie.get("rating", "")
            genres = ", ".join(movie.get("genres", [])) if movie.get("genres") else ""
            st.markdown(f"**{title}** ({year})")
            if rating:
                st.caption(f"⭐ {rating}/10 · {genres}")


def render_trace(trace):
    if not trace:
        st.info("Chưa có trace ReAct.")
        return
    for step in trace:
        with st.expander(f"Bước {step['step']}", expanded=False):
            if step.get("thought"):
                st.markdown(f"**Thought:** {step['thought']}")
            if step.get("action"):
                st.markdown(f"**Action:** `{step['action']}`")
            if step.get("observation"):
                try:
                    obs = json.loads(step["observation"])
                    # Show banner image in trace if available
                    for key in ("movies", "comparison"):
                        for m in obs.get(key, []):
                            if isinstance(m, dict) and m.get("backdrop_url"):
                                st.image(m["backdrop_url"], caption=m.get("title", ""), use_container_width=True)
                                break
                        else:
                            continue
                        break
                    else:
                        if obs.get("backdrop_url"):
                            st.image(obs["backdrop_url"], caption=obs.get("title", ""), use_container_width=True)
                    st.json(obs)
                except json.JSONDecodeError:
                    st.code(step["observation"])
            elif step.get("raw") and not step.get("action"):
                st.text(step["raw"])


def run_query(mode: str, user_input: str, provider: str, model: str, max_steps: int):
    if is_clear_off_topic(user_input):
        return build_off_topic_result(user_input)

    llm = get_llm_provider(provider=provider, model=model)
    if mode == "ReAct Agent v2":
        return ReActAgentV2(llm=llm, tools=TOOL_SPECS, max_steps=max_steps).run(user_input)
    if mode == "ReAct Agent v1":
        return ReActAgent(llm=llm, tools=TOOL_SPECS, max_steps=max_steps).run(user_input)
    return ChatbotBaseline(llm=llm).run(user_input)


init_session()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Cấu hình")
    mode = st.radio("Chế độ", ["ReAct Agent v2", "ReAct Agent v1", "Chatbot Baseline"], index=0)

    st.divider()
    st.subheader("🤖 Chọn Model")
    model_options = build_model_options()
    selected_models = st.multiselect(
        "Provider / Model (1 = chat, 2+ = so sánh song song)",
        options=model_options,
        default=model_options[:1] if model_options else [],
        max_selections=4,
    )

    max_steps = st.slider("Max ReAct steps", 2, 8, 5)

    if not os.getenv("OPENAI_API_KEY"):
        st.warning("Thiếu `OPENAI_API_KEY` trong `.env`.")
    if not os.getenv("TMDB_API_KEY"):
        st.warning("Thiếu `TMDB_API_KEY` — tools TMDB sẽ không hoạt động.")

    st.divider()
    st.subheader("🔧 Tools (7)")
    for tool in TOOL_SPECS:
        st.markdown(f"**`{tool['name']}`** — {tool['description'][:70]}...")

    st.divider()
    st.subheader("💡 Gợi ý câu hỏi")
    for idx, prompt in enumerate(EXAMPLE_PROMPTS):
        if st.button(prompt, key=f"ex_{idx}"):
            st.session_state.pending_prompt = prompt

# ── Main ───────────────────────────────────────────────────────────────────────
st.title("🎬 Movie Recommendation Demo")
st.caption("Chatbot baseline vs ReAct Agent · 7 TMDB tools · Chọn 2+ models để so sánh song song.")

if not selected_models:
    st.info("Chọn ít nhất 1 model ở sidebar để bắt đầu.")
    st.stop()

# ── Comparison mode (2+ models) ────────────────────────────────────────────────
if len(selected_models) >= 2:
    st.subheader(f"📊 So sánh {len(selected_models)} models song song")
    pending = st.session_state.pop("pending_prompt", None)
    if pending:
        st.session_state.cmp_query = pending
        st.session_state.cmp_input = pending

    cmp_query = st.text_input(
        "Câu hỏi để so sánh:",
        value=st.session_state.cmp_query,
        key="cmp_input",
    )
    st.session_state.cmp_query = cmp_query

    run_all = st.button("▶ Chạy tất cả", type="primary", disabled=not cmp_query.strip())
    if (run_all or pending) and cmp_query.strip():
        with st.spinner(f"Đang chạy {len(selected_models)} models song song..."):
            st.session_state.cmp_results = run_parallel_comparison(
                selected_models, mode, cmp_query.strip(), max_steps, run_query
            )

    if st.session_state.cmp_results:
        cols = st.columns(len(selected_models))
        for col, key in zip(cols, selected_models):
            render_comparison_result(col, key, st.session_state.cmp_results.get(key, {}), render_trace)
        st.divider()
        st.subheader("📈 Metrics so sánh")
        render_metrics_table(selected_models, st.session_state.cmp_results)

# ── Single chat mode ───────────────────────────────────────────────────────────
else:
    provider, model = selected_models[0].split("/", 1)
    col_chat, col_trace = st.columns([1.2, 1])

    with col_chat:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("metrics"):
                    m = msg["metrics"]
                    st.caption(
                        f"⏱ {m.get('latency_ms', 0)} ms · {m.get('model', '—')} · "
                        f"steps: {m.get('steps', '—')} · "
                        f"tokens: {(m.get('usage') or {}).get('total_tokens', '—')}"
                    )

        pending = st.session_state.pop("pending_prompt", None)
        user_input = st.chat_input("Hỏi về phim...") or pending

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Đang suy luận..."):
                    try:
                        result = run_query(mode, user_input, provider, model, max_steps)
                        answer = result["answer"]
                        st.markdown(answer)


                        metrics = {
                            "model": model,
                            "latency_ms": result.get("latency_ms"),
                            "usage": result.get("usage"),
                            "steps": result.get("steps"),
                            "mode": result.get("mode"),
                        }
                        st.caption(
                            f"⏱ {metrics.get('latency_ms', 0)} ms · "
                            f"model: {model} · "
                            f"mode: {metrics.get('mode')} · "
                            f"steps: {metrics.get('steps', '—')}"
                        )

                        st.session_state.last_trace = result.get("trace")
                        st.session_state.last_metrics = metrics
                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer, "metrics": metrics}
                        )

                        trace_movies = extract_movies_from_trace(result.get("trace"))
                        if trace_movies:
                            render_movie_cards(trace_movies)
                    except Exception as exc:
                        st.error(f"Lỗi: {exc}")
                        st.info("Kiểm tra `OPENAI_API_KEY` trong `.env`.")

    with col_trace:
        st.subheader("ReAct Trace")
        if mode in ("ReAct Agent v1", "ReAct Agent v2"):
            render_trace(st.session_state.last_trace)
        else:
            st.info("Chuyển sang **ReAct Agent** để xem trace.")
        if st.session_state.last_metrics:
            st.subheader("Metrics")
            st.json(st.session_state.last_metrics)
        if st.button("Xóa lịch sử"):
            st.session_state.messages = []
            st.session_state.last_trace = None
            st.session_state.last_metrics = None
            st.rerun()
