"""Agent v2: improved system prompt, error recovery, and retry logic.

Key improvements over v1 (based on failure analysis in logs/2026-06-01.log):
- llama3.2:3b repeatedly called filter_by_mood() / search_movies() with no args
- Added concrete few-shot examples per tool so small models know exact call format
- Error recovery: when observation contains 'Invalid arguments', inject format hint
- Retry logic: up to 2 retries when no valid Action found before giving up the step
"""

from typing import Any, Dict, List, Optional

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.registry import TOOL_SPECS


class ReActAgentV2(ReActAgent):
    """ReAct agent v2 — same loop as v1 with three targeted improvements."""

    MAX_FORMAT_RETRIES = 2

    def get_system_prompt(self) -> str:
        tool_lines = []
        for tool in self.tools:
            tool_lines.append(f"- {tool['name']}: {tool['description']}")
            if tool.get("example"):
                tool_lines.append(f"  Example: Action: {tool['example']}")

        tools_block = "\n".join(tool_lines)
        return f"""You are a movie recommendation ReAct agent with live TMDB API tools.

Available tools:
{tools_block}

STRICT FORMAT — follow exactly or the tool will fail:

Each step must be ONE of:
  a) Thought + Action (when you need data):
       Thought: <your reasoning>
       Action: tool_name(arg1, arg2)
  b) Final Answer (only when you have enough data):
       Final Answer: <recommendation in Vietnamese or English matching the user>

CORRECT examples (arguments are required — never call with empty parentheses):
  Action: search_movies("Inception", 5)
  Action: filter_by_mood("sad", 5)
  Action: get_movie_details(27205)
  Action: get_trending_movies("VN", "Sci-Fi", "week")
  Action: get_similar_movies(27205, 5)
  Action: check_streaming_availability(27205, "VN")
  Action: compare_movies([27205, 157336, 1124])

WRONG — do not do this:
  Action: filter_by_mood()      ← missing required 'mood' argument
  Action: search_movies()       ← missing required 'query' argument
  Action: get_movie_details()   ← missing required 'movie_id' argument

Additional rules:
- If a request is not clearly about movies, series, cinemas, streaming, or watch recommendations, do not call tools and do not invent a movie angle. Reply with a short Final Answer saying this demo only handles movie-related questions.
- Search for a movie first with search_movies() to get the correct movie_id.
- Never invent movie_id values.
- Valid moods: happy, sad, relaxed, excited, romantic, scary.
- Use at most one Action per step. Stop when you have enough data.
"""

    def run(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_V2_START", {"input": user_input, "model": self.llm.model_name})

        trace: List[Dict[str, Any]] = []
        scratchpad = f"Question: {user_input}\n"
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_latency = 0
        final_answer: Optional[str] = None
        steps = 0
        format_retries = 0

        while steps < self.max_steps:
            prompt = scratchpad + "\nYour next step:"
            result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            content = result.get("content", "")
            total_latency += result.get("latency_ms", 0)

            usage = result.get("usage") or {}
            for key in total_usage:
                total_usage[key] += usage.get(key, 0)

            parsed = self._parse_llm_step(content)
            step_record: Dict[str, Any] = {
                "step": steps + 1,
                "thought": parsed["thought"],
                "action": parsed["action"],
                "observation": None,
                "raw": content,
            }

            if parsed["final_answer"]:
                final_answer = parsed["final_answer"]
                trace.append(step_record)
                break

            if parsed["action"]:
                observation = self._execute_tool(parsed["action"])
                step_record["observation"] = observation
                trace.append(step_record)
                format_retries = 0

                # Error recovery: inject explicit format hint when tool args are wrong
                if "Invalid arguments" in observation:
                    scratchpad += (
                        f"\nThought: {parsed['thought'] or ''}\n"
                        f"Action: {parsed['action']}\n"
                        f"Observation: {observation}\n"
                        "HINT: The tool failed due to missing or wrong arguments. "
                        "Check the CORRECT examples in the system prompt and include ALL required arguments.\n"
                    )
                else:
                    scratchpad += (
                        f"\nThought: {parsed['thought'] or ''}\n"
                        f"Action: {parsed['action']}\n"
                        f"Observation: {observation}\n"
                    )
            else:
                # Retry logic: re-prompt with format reminder before giving up the step
                format_retries += 1
                trace.append(step_record)
                if format_retries <= self.MAX_FORMAT_RETRIES:
                    scratchpad += (
                        f"\n{content}\n"
                        "REMINDER: output a valid Action in this exact format:\n"
                        "Thought: <reason>\nAction: tool_name(arg1, arg2)\n"
                        "OR if done: Final Answer: <answer>\n"
                    )
                else:
                    scratchpad += (
                        f"\n{content}\n"
                        "Observation: No valid Action after retries. "
                        "Please provide Final Answer now.\n"
                    )
                    format_retries = 0

            steps += 1

        if not final_answer:
            final_answer = (
                "Không thể hoàn thành trong số bước cho phép. "
                "Hãy thử câu hỏi cụ thể hơn hoặc tăng max_steps."
            )

        logger.log_event("AGENT_V2_END", {"steps": steps, "trace_len": len(trace)})
        return {
            "answer": final_answer,
            "trace": trace,
            "steps": steps,
            "usage": total_usage,
            "latency_ms": total_latency,
            "mode": "react_agent_v2",
        }
