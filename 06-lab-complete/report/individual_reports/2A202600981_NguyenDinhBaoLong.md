# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Đình Bảo Long
- **Student ID**: 2A202600981
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

*Implemented the **Display Banner for Movie** feature — enriching the Streamlit UI with visual movie posters, backdrop banners, and metadata cards extracted from the ReAct agent's trace.*

- **Modules Implemented**:
  - `src/tools/tmdb_client.py` — Extended the TMDB data layer to include image URLs.
  - `src/app.py` — Built the UI rendering pipeline for movie banners and poster cards.

- **Code Highlights**:

  **1. TMDB Image URL Integration (`src/tools/tmdb_client.py`)**

  Added the `TMDB_IMAGE_BASE` constant and extended both `summarize()` and `get_movie_details()` to return `poster_url` and `backdrop_url`:

  ```python
  TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

  # In summarize() — used by search, trending, similar, discover endpoints
  "poster_url": f"{TMDB_IMAGE_BASE}/w500{movie['poster_path']}" if movie.get("poster_path") else None,
  "backdrop_url": f"{TMDB_IMAGE_BASE}/w1280{movie['backdrop_path']}" if movie.get("backdrop_path") else None,

  # In get_movie_details() — used by detail and compare tools
  "poster_url": f"{TMDB_IMAGE_BASE}/w500{data['poster_path']}" if data.get("poster_path") else None,
  "backdrop_url": f"{TMDB_IMAGE_BASE}/w1280{data['backdrop_path']}" if data.get("backdrop_path") else None,
  ```

  **2. Trace Movie Extraction (`src/app.py` — `extract_movies_from_trace()`)**

  Parses the ReAct agent's JSON trace observations to collect all unique movies with poster images, handling both single-detail and list-based responses:

  ```python
  def extract_movies_from_trace(trace):
      movies = []
      seen_ids = set()
      for step in trace:
          obs = json.loads(step.get("observation", "{}"))
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
  ```

  **3. Movie Card Grid Renderer (`src/app.py` — `render_movie_cards()`)**

  Renders a responsive grid of movie poster cards with title, year, rating, and genres:

  ```python
  def render_movie_cards(movies, max_cols=4):
      cols = st.columns(min(len(movies), max_cols))
      for idx, movie in enumerate(movies[:max_cols * 2]):
          col = cols[idx % max_cols]
          with col:
              if movie.get("poster_url"):
                  st.image(movie["poster_url"], use_container_width=True)
              st.markdown(f"**{movie.get('title', '')}** ({movie.get('year', '')})")
              if movie.get("rating"):
                  st.caption(f"⭐ {movie['rating']}/10 · {', '.join(movie.get('genres', []))}")
  ```

  **4. Backdrop Banner in ReAct Trace (`src/app.py` — `render_trace()`)**

  Enhanced the trace viewer to display `backdrop_url` images (1280px wide cinematic banners) inline within each trace step's observation:

  ```python
  # Show banner image in trace if available
  for key in ("movies", "comparison"):
      for m in obs.get(key, []):
          if isinstance(m, dict) and m.get("backdrop_url"):
              st.image(m["backdrop_url"], caption=m.get("title", ""), use_container_width=True)
              break
  ```

- **Documentation**:

  The banner display feature interacts with the ReAct loop as follows:
  1. The ReAct Agent calls TMDB tools (search, similar, trending, detail, etc.) during its `Action` steps.
  2. Each tool returns an `Observation` JSON containing movie data — my code in `tmdb_client.py` ensures this data now includes `poster_url` (w500) and `backdrop_url` (w1280).
  3. After the agent produces a final `Answer`, my `extract_movies_from_trace()` function walks the entire trace and collects unique movies with images.
  4. `render_movie_cards()` then displays them as a visual grid below the text answer.
  5. Additionally, within the ReAct Trace panel, backdrop banners are shown inline for each observation step, giving a visual preview of what the agent "saw".

---

## II. Debugging Case Study (10 Points)

*Encountered an issue where movie poster images were not appearing for certain tool responses.*

- **Problem Description**: When the agent used `search_movies()` or `trending_movies()`, the returned movie data did not include any image URLs. The UI rendered the text answer correctly, but the movie card grid was empty — no posters were displayed. The `summarize()` method in `TMDbClient` was only returning `id`, `title`, `year`, `genres`, and `rating`, but had no `poster_url` or `backdrop_url` fields.

- **Log Source**: Inspecting the trace JSON in the Streamlit "ReAct Trace" expander revealed that observation payloads looked like:
  ```json
  {
    "id": 27205,
    "title": "Inception",
    "year": 2010,
    "genres": ["Action", "Science Fiction"],
    "rating": 8.4
  }
  ```
  The `poster_path` and `backdrop_path` raw fields existed in the TMDB API response, but were never transformed into full URLs by `summarize()`.

- **Diagnosis**: The root cause was in the data layer, not the LLM or the prompt. The `summarize()` method in `tmdb_client.py` was designed to return a lightweight dictionary for the agent's reasoning, but it discarded the image paths. Similarly, `get_movie_details()` did not construct image URLs. The TMDB API returns relative paths like `/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg`, which need to be prefixed with `https://image.tmdb.org/t/p/w500` to become usable URLs. Without the `TMDB_IMAGE_BASE` constant and the URL construction logic, the UI had no images to render.

- **Solution**:
  1. Added the `TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"` constant at module level.
  2. Extended `summarize()` to construct `poster_url` (using `/w500` size) and `backdrop_url` (using `/w1280` size) from the raw TMDB paths, with `None` fallback when no image exists.
  3. Applied the same pattern to `get_movie_details()` for consistency.
  4. Used safe access with `movie.get("poster_path")` to avoid `KeyError` on movies without images.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: The `Thought` block gave the ReAct agent a significant advantage over the direct Chatbot answer. For example, when asked *"Tôi vừa xem Inception, gợi ý phim tương tự có trên Netflix"*, the Chatbot simply generated a list of similar movies from its training data (which may be outdated). The ReAct agent, however, produced a `Thought` like *"I need to first find Inception's ID, then use similar_movies to get actual similar films, and finally check watch_providers to see which are on Netflix VN"*. This multi-step reasoning led to more accurate, real-time results backed by actual TMDB data. The `Thought` block essentially served as the agent's planning scratchpad, breaking a complex query into executable sub-tasks.

2. **Reliability**: The Agent performed *worse* than the Chatbot in two scenarios:
   - **Simple factual questions** (e.g., "Ai đạo diễn phim Parasite?") — the Chatbot answered instantly from its training data, while the Agent made unnecessary API calls, adding latency without improving accuracy.
   - **When TMDB API was rate-limited or returned errors** — the Agent sometimes got stuck retrying failed tool calls or produced confusing partial answers, while the Chatbot always gave a coherent (if potentially outdated) response. The Chatbot's reliability came from having no external dependencies, while the Agent's reliability was constrained by its tool ecosystem.

3. **Observation**: The environment feedback (observations) had a critical influence on the agent's next steps. For instance, when `search_movies("Inception")` returned multiple results, the observation helped the agent pick the correct movie ID (27205) rather than guessing. When `watch_providers` returned an empty `streaming` list for a particular country, the agent adapted its answer to say the movie wasn't available for streaming and suggested alternatives. The observations essentially "grounded" the agent in reality — without them, the agent would hallucinate movie availability, ratings, and streaming platforms just like the Chatbot sometimes did.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Implement caching for TMDB API responses using Redis or `st.cache_data` with longer TTL. Currently, every user query triggers fresh API calls. For a production system, movie metadata (posters, ratings, genres) changes infrequently and could be cached for hours. Additionally, using an asynchronous HTTP client (e.g., `httpx.AsyncClient`) instead of synchronous `requests` would improve throughput when the agent makes multiple parallel tool calls.

- **Safety**: Add an input validation layer before tool execution to sanitize user queries and prevent injection attacks through crafted movie titles. Implement a "Supervisor" pattern where a secondary LLM reviews the agent's planned actions before execution — for example, flagging if the agent attempts to call tools with unexpected parameters or enters a loop of repeated identical calls. Rate limiting per user session would also prevent abuse.

- **Performance**: Replace the sequential movie detail fetching with batch requests. Currently, `extract_movies_from_trace()` processes the trace after completion. A streaming approach — rendering movie cards as each observation arrives — would reduce perceived latency. For the image rendering specifically, implementing lazy loading with placeholder shimmer effects would improve the initial page load time, especially when displaying 8+ movie posters simultaneously.

---

> [!NOTE]
> Report submitted as `2A202600981_NguyenDinhBaoLong.md` in the `report/individual_reports/` folder.
