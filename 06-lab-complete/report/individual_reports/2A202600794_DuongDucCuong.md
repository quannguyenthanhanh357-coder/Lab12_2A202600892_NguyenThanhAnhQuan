# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Dương Đức Cường
- **Student ID**: 2A202600794
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

My main contribution was implementing the core ReAct loop in `src/agent/agent.py`.
Before this change, the agent skeleton only contained TODO comments and returned a placeholder response.
I completed the logic that allows the agent to repeatedly call the LLM, parse actions, execute tools, feed observations back into the prompt, and stop when a final answer is produced.

- **Modules Implemented**:
  - `src/agent/agent.py`
  - `tests/test_react_agent.py`
  - `streamlit_app.py`

- **Code Highlights**:
  - Implemented `ReActAgent.run()` to support the full Thought -> Action -> Observation -> Final Answer cycle.
  - Added telemetry events for `AGENT_START`, `AGENT_STEP`, `TOOL_CALL`, `TOOL_ERROR`, `AGENT_PARSE_ERROR`, and `AGENT_END`.
  - Integrated `PerformanceTracker.track_request()` so every LLM call records token usage, latency, and estimated cost.
  - Implemented action parsing for model outputs such as `Action: add(a=2, b=3)`.
  - Implemented dynamic tool execution using callable functions attached to the tool definitions.
  - Added offline tests with a deterministic `FakeProvider`, so the ReAct loop can be tested without OpenAI, Gemini, or a local model.
  - Added a Streamlit demo to visualize reasoning steps, tool calls, observations, final answers, and telemetry logs.

- **Documentation**:
  - The ReAct loop starts with the user question.
  - The LLM returns either an `Action` or a `Final Answer`.
  - If the LLM returns an `Action`, the agent parses the tool name and arguments, runs the matching tool, then appends the tool result as an `Observation`.
  - The updated prompt is sent back to the LLM so the model can reason using real tool feedback.
  - This process repeats until the model returns `Final Answer` or the agent reaches `max_steps`.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  During testing, I simulated a common ReAct failure: the model hallucinated a tool that did not exist.
  The fake LLM output was:

```text
Thought: I should use a tool.
Action: subtract(a=3, b=1)
```

  However, the agent was initialized with no available tools. This means `subtract` was not a valid tool.

- **Log Source**:
  The event was recorded in `logs/2026-06-01.log`:

```json
{"event": "TOOL_ERROR", "data": {"tool": "subtract", "error": "Tool subtract not found."}}
```

- **Diagnosis**:
  The failure happened because the LLM tried to act outside the tool inventory.
  This is a typical agentic failure mode: the model can produce a plausible-looking action even when the system has not actually provided that tool.
  A normal chatbot would likely answer directly, but a ReAct agent must obey the available tool list.

- **Solution**:
  I added explicit tool validation in `_execute_tool()`.
  If the requested tool does not exist, the agent does not crash.
  Instead, it logs a `TOOL_ERROR` event and feeds the observation `Tool subtract not found.` back into the next LLM prompt.
  In the test case, the model then produced a safe final answer:

```text
Final Answer: I cannot use subtract because that tool is not available.
```

This demonstrates a useful guardrail: tool hallucinations become observable failures instead of silent incorrect behavior.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   The `Thought` step helps expose the model's intermediate plan.
   A chatbot usually gives a direct answer, which can hide whether it guessed or reasoned correctly.
   In contrast, the ReAct agent separates reasoning from action, making it easier to inspect how the answer was produced.

2. **Reliability**:
   The ReAct agent is more reliable for multi-step tasks that require external tools or calculations.
   However, it can perform worse than a chatbot in simple Q&A because it has extra latency, more tokens, and more failure points such as parser errors, invalid arguments, or hallucinated tools.

3. **Observation**:
   Observation is the key difference between a chatbot and an agent.
   The agent does not only rely on the model's internal knowledge; it can use feedback from the environment.
   In the successful test, the `add` tool returned `5`, and that observation was inserted into the next prompt before the final answer was generated.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  Add asynchronous tool execution for slow external APIs, especially search, database, or web browsing tools.

- **Safety**:
  Add stricter argument validation before executing tools.
  For example, each tool could define a Pydantic schema so invalid or unsafe arguments are rejected before runtime.

- **Performance**:
  Add better telemetry aggregation to compare Chatbot, Agent v1, and Agent v2 by success rate, average latency, token count, cost estimate, and loop count.

- **Production Readiness**:
  Add retry logic for malformed model outputs and a supervisor layer that checks whether the selected tool is appropriate before execution.

---

## Test Evidence

I added two offline tests in `tests/test_react_agent.py`:

- `test_react_agent_executes_tool_and_returns_final_answer`
- `test_react_agent_feeds_unknown_tool_error_back_to_model`

Both tests passed with:

```text
python -m pytest tests\test_react_agent.py -q
2 passed
```

I also added a visual demo that can be launched with:

```text
python -m streamlit run streamlit_app.py
```
