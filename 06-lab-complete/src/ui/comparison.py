"""Multi-model parallel comparison utilities for the demo app."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
from typing import Any, Callable, Dict, List

import streamlit as st


@st.cache_data(ttl=30)
def build_model_options() -> List[str]:
    """Return list of 'provider/model' strings for all available providers.
    Cached 30s to avoid repeated HTTP calls to Ollama on every re-render.
    """
    from src.core.factory import DEEPSEEK_MODELS, GEMINI_MODELS, OPENAI_MODELS, is_local_provider_available
    from src.core.gemini_provider import list_available_models as list_gemini_models
    from src.core.ollama_provider import is_ollama_running, list_available_models

    options = [f"openai/{m}" for m in OPENAI_MODELS]
    options += [f"deepseek/{m}" for m in DEEPSEEK_MODELS]
    if os.getenv("GEMINI_API_KEY"):
        gemini_models = list_gemini_models(api_key=os.getenv("GEMINI_API_KEY")) or list(GEMINI_MODELS)
        preferred = [m for m in GEMINI_MODELS if m in gemini_models]
        extras = [m for m in gemini_models if m not in preferred]
        options += [f"gemini/{m}" for m in preferred + extras[:2]]
    if is_ollama_running():
        ollama_models = list_available_models() or ["llama3.2:3b"]
        options += [f"ollama/{m}" for m in ollama_models]
    local_model_path = Path(os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"))
    if not local_model_path.is_absolute():
        local_model_path = Path(__file__).resolve().parents[2] / local_model_path
    if is_local_provider_available() and local_model_path.exists():
        options += [f"local/{local_model_path.name}"]
    return options


def run_parallel_comparison(
    selected_models: List[str],
    mode: str,
    query: str,
    max_steps: int,
    run_fn: Callable,
) -> Dict[str, Any]:
    """Run multiple provider/model combos in parallel via ThreadPoolExecutor."""

    def _run_one(key: str):
        provider, model = key.split("/", 1)
        try:
            res = run_fn(mode, query, provider, model, max_steps)
            return key, {"ok": True, **res}
        except Exception as exc:
            return key, {"ok": False, "error": str(exc), "answer": f"Lỗi: {exc}"}

    results: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(selected_models)) as executor:
        futures = {executor.submit(_run_one, key): key for key in selected_models}
        for future in as_completed(futures):
            key, result = future.result()
            results[key] = result
    return results


def render_comparison_result(
    col,
    label: str,
    result: Dict[str, Any],
    render_trace_fn: Callable,
) -> None:
    """Render one model result inside a Streamlit column."""
    with col:
        provider, model = label.split("/", 1)
        st.markdown(f"#### `{provider}` / `{model}`")
        st.divider()

        if not result:
            st.warning("Không có kết quả.")
            return

        if not result.get("ok", True):
            st.error(result.get("error", "Lỗi không xác định"))
            return

        st.markdown(result.get("answer", ""))

        if result.get("trace"):
            with st.expander(f"ReAct Trace ({result.get('steps', 0)} bước)"):
                render_trace_fn(result["trace"])

        usage = result.get("usage") or {}
        st.caption(
            f"⏱ {result.get('latency_ms', 0)} ms · "
            f"steps: {result.get('steps', '—')} · "
            f"tokens: {usage.get('total_tokens', '—')}"
        )


def render_metrics_table(selected_models: List[str], results: Dict[str, Any]) -> None:
    """Render comparison metrics as a DataFrame + latency bar chart."""
    import pandas as pd

    rows = []
    for key in selected_models:
        res = results.get(key, {})
        usage = res.get("usage") or {}
        rows.append({
            "Model": key,
            "Status": "✅" if res.get("ok", True) and "error" not in res else "❌",
            "Latency (ms)": res.get("latency_ms", 0),
            "Steps": res.get("steps", "—"),
            "Prompt tokens": usage.get("prompt_tokens", "—"),
            "Completion tokens": usage.get("completion_tokens", "—"),
            "Total tokens": usage.get("total_tokens", "—"),
            "Mode": res.get("mode", "—"),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    latency_data = {r["Model"]: r["Latency (ms)"] for r in rows if isinstance(r["Latency (ms)"], (int, float)) and r["Latency (ms)"] > 0}
    if len(latency_data) >= 2:
        st.caption("📊 Latency so sánh (ms)")
        st.bar_chart(latency_data)
