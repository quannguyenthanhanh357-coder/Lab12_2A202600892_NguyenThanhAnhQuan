"""Small deterministic mock LLM used when no provider API key is configured."""


def ask(question: str, delay: float = 0.0) -> str:
    question_lower = question.lower()
    if "docker" in question_lower:
        return "Docker packages the app and its runtime so it can run consistently across environments."
    if "deploy" in question_lower or "deployment" in question_lower:
        return "Deployment ships the agent to a server or cloud platform where users can reach it."
    if "health" in question_lower:
        return "The agent is healthy and ready to answer requests."
    return "This is a mock AI response. In production, replace it with a real LLM provider call."
