# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Thanh Anh Quân
- **Student ID**: 2A202600892
- **Date**: June 1, 2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

### 1. Project Ideation & Scope
- **Concept**: Proposed a "Movie Recommendation Agent" system combining ReAct (Reasoning + Acting) with live TMDB APIs.
- **Goal**: Demonstrate difference between simple Chatbot (direct answers, hallucination risk) vs. ReAct Agent (reasoning + environment feedback + live data).
- **Key insight**: Showed how agents can chain multiple tools autonomously to answer complex user queries.

### 2. Core Tool Implementation: `search_movies()`
- **Module**: [`src/tools/movie_tools.py` lines 100-120](src/tools/movie_tools.py#L100-L120)
- **Function signature**: `search_movies(query: str, limit: int = 5) -> str`
- **Purpose**: Search TMDB movies by title/keyword—**foundational tool** for all movie discovery workflows.
- **Returns**: JSON with movie_id, title, year, genres, rating (enough data for agent to decide next action).
- **Error handling**: Validates empty query, caps limit to [1, 10], returns JSON errors for agent retry.

### 3. Tool Registration in TOOL_SPECS
- **File**: [`src/tools/registry.py` lines 16-21](src/tools/registry.py#L16-L21)
- **Added**: Entry in `TOOL_SPECS` list with:
  - Clear description: "Search TMDB by title/keyword. Args: query (str), limit (int)..."
  - Usage example: `search_movies("Inception", 5)` for ReAct agent to understand correct format.
  - Registered in `TOOL_MAP` for executor to invoke.

### 4. Integration with ReAct Loop
- **How it works**: When user asks "Find Inception", agent calls `search_movies("Inception", 5)` → receives [27205, title, rating] → can chain to `get_movie_details(27205)` or `get_similar_movies(27205)` based on observation.
- **Core of recommendation flow**: All other tools depend on search_movies to bootstrap from user text query → machine-readable movie_id.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: 
  - **Initial failure**: When `search_movies()` returned results, agent sometimes wouldn't extract the `movie_id` field correctly to pass to `get_movie_details()`.
  - **Root cause**: JSON response format from `search_movies()` wasn't matching agent's parsing expectations.
  - **Symptom**: Agent would say "Found Inception" but then couldn't retrieve details, breaking the recommendation chain.

- **Log Source**: 
  - Reference: [`logs/2026-06-01.log`](logs/2026-06-01.log) - Check early failed attempts before successful runs.
  - Example log entry showing tool call:
    ```json
    {"event": "TOOL_CALL", "tool": "search_movies", "args": ["Inception", 5]}
    ```

- **Diagnosis**: 
  - **Problem**: `search_movies()` wrapped results in nested `"movies"` array, but agent expected flat JSON structure.
  - **Impact**: When agent tried to access `observation[0]["id"]`, it got `undefined` because structure was `observation["movies"][0]["id"]`.
  - **Why it happened**: Initial implementation followed generic pattern without testing agent's observation parsing.

- **Solution**: 
  - **Standardized JSON response format** in [`src/tools/movie_tools.py` lines 110-120](src/tools/movie_tools.py#L110-L120): Ensured `search_movies()` returns flat structure:
    ```json
    {"query": "...", "movies": [{"id": 27205, "title": "Inception", ...}]}
    ```
  - **Updated TOOL_SPECS example** [`src/tools/registry.py` line 20](src/tools/registry.py#L20): Made example call explicit so agent knows exact format.
  - **Result**: Tool chains now work reliably; agent can execute search_movies → get_movie_details → compare_movies in sequence (verified in 2026-06-01 logs).

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning - `Thought` block advantage**:
   - **Chatbot**: "Find Inception" → Direct LLM output (may use outdated knowledge, wrong IMDB vs TMDB rating).
   - **ReAct Agent**: Same query → `Thought: I need to search TMDB for Inception` → `Action: search_movies("Inception", 5)` → Observation: Real-time TMDB data with current ratings → `Thought: Found it with id=27205, now get details` → `Action: get_movie_details(27205)` → Live metadata.
   - **Why better**: `Thought` forces agent to state reasoning *before* acting; agent must validate each step. Chatbot might say "Inception (2010)" which is outdated.

2.  **Reliability - Agent *worse* than Chatbot**:
   - **Scenario 1**: Ambiguous query ("Recommend action movies") → ReAct tries search_movies with "action" as title, gets wrong results; Chatbot can use semantic understanding to map "action" → genre filter.
   - **Scenario 2**: Non-existent movie → Agent loops searching 10x; Chatbot immediately says "Not found".
   - **Scenario 3**: User typo ("Incepton") → Agent finds nothing; Chatbot with spell-check catches it.
   - **Trade-off**: Agent sacrifices *flexibility* to gain *data accuracy*.

3.  **Environment feedback influence**:
   - **Observation shapes strategy**: When `search_movies("action")` returns 5 results, agent reads genres/ratings to decide: Should I get_similar_movies for more, or present these?
   - **Error recovery**: If observation says `{"error": "Limit must be 1-10"}`, agent learns the constraint and retries with valid limit.
   - **Chain dependencies**: If `search_movies()` returns 3 movies but user asked for "best action film", agent reads ratings from observation and either picks the top one or calls `get_similar_movies()` to expand search. **The quality of observation data directly determines recommendation quality.**

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: 
  - **Parallel tool execution**: Use `asyncio.gather()` to run multiple searches simultaneously (e.g., search_movies + get_trending_movies in parallel rather than sequentially).
  - **Batch TMDB requests**: If agent needs details for 5 movies, batch them into 1-2 API calls instead of 5 sequential calls.
  - **Response caching**: Cache recent search_movies queries by title (e.g., Redis with 1-hour TTL) to reduce TMDB API usage for popular titles.

- **Safety**: 
  - **Input sanitization**: Validate `search_movies()` query to prevent TMDB injection attacks or malformed requests.
  - **Rate limiting**: Cap per-user search_movies calls (e.g., 50 calls/hour) to prevent API quota exhaustion.
  - **Tool audit layer**: Add a "Supervisor" LLM to review agent tool selections before execution (e.g., detect if agent calls search_movies with empty query).

- **Performance**: 
  - **Semantic tool selection**: With 10+ tools, use embedding-based search to rank relevant tools instead of full TOOL_SPECS scan per query.
  - **Smart routing**: For simple queries (1 search_movies + 1 get_movie_details), use fast small models (llama3.2); for complex chains, use GPT-4.
  - **Prompt caching**: Store TOOL_SPECS + system prompt in cache (OpenAI prompt cache feature) to reduce tokens on repeated agent calls.

---


