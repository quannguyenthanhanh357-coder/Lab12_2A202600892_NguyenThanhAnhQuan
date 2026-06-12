import re
from typing import Any, Dict, List, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.registry import TOOL_SPECS, execute_tool, parse_action


class ReActAgent:
    """ReAct agent: Thought -> Action -> Observation loop for movie recommendations."""

    def __init__(self, llm: LLMProvider, tools: Optional[List[Dict[str, Any]]] = None, max_steps: int = 5):
        self.llm = llm
        self.tools = tools or TOOL_SPECS
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []

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

Rules:
1. Always use tools to fetch facts from TMDB before recommending. Never invent movie_id or ratings.
2. If you only know a movie title, call search_movies first to get the TMDB movie_id.
3. Respond ONLY in this format for each step (no markdown code blocks):
Thought: <reasoning>
Action: tool_name(args)
4. After Observation, continue with Thought/Action OR finish with:
Final Answer: <recommendation in Vietnamese or English matching the user>
5. Use at most one Action per step. Stop when you have enough data.
6. Valid moods for filter_by_mood: happy, sad, relaxed, excited, romantic, scary.
7. If a request is not clearly about movies, series, cinemas, streaming, or watch recommendations, do not call tools and do not invent a movie angle. Reply with a short Final Answer saying this demo only handles movie-related questions.
"""

    def _parse_llm_step(self, content: str) -> Dict[str, Optional[str]]:
        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|$)", content, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r"Action:\s*(.+?)(?=\n|$)", content, re.IGNORECASE)
        final_match = re.search(r"Final Answer:\s*(.+)", content, re.DOTALL | re.IGNORECASE)

        return {
            "thought": thought_match.group(1).strip() if thought_match else None,
            "action": action_match.group(1).strip() if action_match else None,
            "final_answer": final_match.group(1).strip() if final_match else None,
            "raw": content,
        }

    def _execute_tool(self, action_line: str) -> str:
        try:
            name, args = parse_action(action_line)
        except ValueError as exc:
            return f'{{"error": "{exc}"}}'

        observation = execute_tool(name, args)
        logger.log_event("TOOL_CALL", {"tool": name, "args": args, "observation_preview": observation[:200]})
        return observation

    def run(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        trace: List[Dict[str, Any]] = []
        scratchpad = f"Question: {user_input}\n"
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_latency = 0
        final_answer = None
        steps = 0

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
                scratchpad += (
                    f"\nThought: {parsed['thought'] or ''}\n"
                    f"Action: {parsed['action']}\n"
                    f"Observation: {observation}\n"
                )
            else:
                trace.append(step_record)
                scratchpad += f"\n{content}\nObservation: No valid Action found. Use Action: tool_name(args) or Final Answer.\n"

            steps += 1

        if not final_answer:
            final_answer = "Không thể hoàn thành trong số bước cho phép. Hãy thử câu hỏi cụ thể hơn hoặc tăng max_steps."

        logger.log_event("AGENT_END", {"steps": steps, "trace_len": len(trace)})
        return {
            "answer": final_answer,
            "trace": trace,
            "steps": steps,
            "usage": total_usage,
            "latency_ms": total_latency,
            "mode": "react_agent",
        }
