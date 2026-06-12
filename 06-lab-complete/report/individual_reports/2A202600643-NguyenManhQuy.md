# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Mạnh Quý
- **Student ID**: 2A202600643
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

Trong lab này, tôi triển khai **hệ thống đa LLM provider**, **ReActAgentV2** với cơ chế phục hồi lỗi, và **giao diện so sánh song song** dựa trên phân tích log thực tế.

- **Modules Implemented**:
  - `src/core/deepseek_provider.py` — Provider DeepSeek qua OpenAI-compatible API, hỗ trợ generate và stream.
  - `src/core/ollama_provider.py` — Provider Ollama cho model local (llama3, mistral, qwen2...), gọi REST tại `localhost:11434`, tối ưu `temperature=0.1` để tool call ổn định hơn.
  - `src/core/factory.py` — Factory `get_llm_provider()` đăng ký lazy-load DeepSeek/Ollama, đọc cấu hình từ env vars.
  - `src/agent/agent_v2.py` — `ReActAgentV2` kế thừa `ReActAgent`, bổ sung few-shot examples, error recovery khi `"Invalid arguments"` xuất hiện trong observation, và retry logic `MAX_FORMAT_RETRIES=2`.
  - `src/ui/comparison.py` — Chạy song song nhiều provider/model bằng `ThreadPoolExecutor`, render bảng metrics và biểu đồ latency.
  - `report/group_report/GROUP_REPORT.md` — Báo cáo nhóm với phân tích telemetry từ log thực tế.

- **Code Highlights**:

  **DeepSeek Provider** — tái sử dụng OpenAI SDK với `base_url` override:
  ```python
  self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
  ```

  **Ollama Provider** — kiểm tra server trước khi gọi, xử lý lỗi kết nối rõ ràng:
  ```python
  if selected == "ollama":
      from src.core.ollama_provider import OllamaProvider
      return OllamaProvider(model_name=..., base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
  ```

  **ReActAgentV2 — Error Recovery** (`src/agent/agent_v2.py`, dòng 108–115):
  ```python
  if "Invalid arguments" in observation:
      scratchpad += (
          f"Observation: {observation}\n"
          "HINT: The tool failed due to missing or wrong arguments. "
          "Check the CORRECT examples in the system prompt and include ALL required arguments.\n"
      )
  ```

  **ReActAgentV2 — Retry Logic** (`src/agent/agent_v2.py`, dòng 124–138):
  ```python
  format_retries += 1
  if format_retries <= self.MAX_FORMAT_RETRIES:
      scratchpad += "REMINDER: output a valid Action in this exact format:..."
  else:
      scratchpad += "Observation: No valid Action after retries. Please provide Final Answer now.\n"
  ```

- **Documentation — tương tác với ReAct loop**:
  1. User chọn provider/model trên sidebar → `get_llm_provider(provider, model)` từ factory khởi tạo đúng implementation.
  2. `ReActAgentV2.run()` gọi `llm.generate(prompt, system_prompt=self.get_system_prompt())` ở mỗi bước.
  3. System prompt v2 chứa ví dụ đúng/sai cụ thể cho từng tool, bổ sung khi model nhỏ không thể suy luận từ mô tả đơn thuần.
  4. Khi observation chứa `"Invalid arguments"`, một `HINT` được inject thẳng vào scratchpad trước lần gọi tiếp theo — không cần thay đổi gì trong tool hoặc parser.

---

## II. Debugging Case Study (10 Points)

### Case: llama3.2:3b — Gọi tool không có argument

- **Problem Description**: Khi hỏi *"Tôi buồn, muốn xem phim nhẹ nhàng — gợi ý 3 phim."*, agent v1 chạy 5 bước liên tiếp đều thất bại, không có Final Answer.

- **Log Source** (`logs/2026-06-01.log`, run #3 với `llama3.2:3b`):
  ```json
  {"event": "TOOL_CALL", "data": {"tool": "filter_by_mood", "args": [],
   "observation_preview": "{\"error\": \"Invalid arguments for filter_by_mood: filter_by_mood() missing 1 required positional argument: 'mood'\"}"}}
  {"event": "TOOL_CALL", "data": {"tool": "search_movies", "args": [], ...}}
  {"event": "TOOL_CALL", "data": {"tool": "search_movies", "args": [], ...}}
  {"event": "TOOL_CALL", "data": {"tool": "search_movies", "args": [], ...}}
  {"event": "TOOL_CALL", "data": {"tool": "search_movies", "args": [], ...}}
  ```
  Kết thúc với `AGENT_END`, `"steps": 5` — không có câu trả lời.

- **Diagnosis**:
  1. **Prompt không đủ ví dụ cụ thể**: System prompt v1 chỉ mô tả tên tool và tham số, không có ví dụ gọi đúng. Model 3B không thể tự suy luận format `Action: filter_by_mood("sad", 5)` từ mô tả.
  2. **Không có feedback loop cho lỗi format**: Khi observation trả về lỗi `"missing argument"`, scratchpad v1 chỉ append nguyên văn observation mà không có gợi ý sửa. Model tiếp tục gọi tool khác (`search_movies`) cũng không có arg — biểu hiện hallucination: biết cần dùng tool nhưng mất track về argument.
  3. **Giới hạn mô hình nhỏ**: GPT-4o và DeepSeek-chat có thể suy luận format từ mô tả; llama3.2:3b (3B params) cần ví dụ tường minh.

- **Solution**:
  - Thêm block `CORRECT examples` với call string đầy đủ cho mỗi tool trong system prompt (`src/agent/agent_v2.py`, `get_system_prompt()`).
  - Thêm block `WRONG` để cảnh báo rõ các trường hợp gọi thiếu argument.
  - Inject `HINT` vào scratchpad ngay khi observation chứa `"Invalid arguments"`.
  - Thêm `MAX_FORMAT_RETRIES=2`: nhắc lại format rules trước khi bỏ bước.
  - Sau fix (Agent v2 + cùng `llama3.2:3b`), dự kiến tool call sẽ có đúng argument ở bước đầu tiên.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: Block `Thought:` trong ReAct buộc model phân rã câu hỏi trước khi hành động. Với truy vấn *"Tìm phim tương tự Inception có trên Netflix VN không?"*, Chatbot trả lời ngay từ training data (dễ hallucinate ID phim và availability); Agent v1/v2 bắt buộc qua bước `search_movies("Inception")` → lấy `movie_id` thực → `get_similar_movies()` → `check_streaming_availability()`. Kết quả grounded, không bịa.

2. **Reliability**: Agent thực sự kém hơn Chatbot ở 2 tình huống:
   - **Câu hỏi fact đơn giản đã có trong training data** ("Ai đạo diễn Inception?"): Chatbot trả lời ngay, Agent mất thêm 1–2 API call và ~1–2 giây.
   - **Model nhỏ + tool spec không rõ**: llama3.2:3b trên Agent v1 có 100% failure rate do format argument, trong khi cùng model dùng Chatbot (không gọi tool) vẫn cho câu trả lời tạm chấp nhận được.

3. **Observation**: Observation từ TMDB định hướng trực tiếp bước tiếp theo qua scratchpad. Khi `search_movies("Inception")` trả về `movie_id=27205`, bước kế tiếp tự nhiên là `get_similar_movies(27205, 5)` mà không cần model "nhớ" hay suy đoán ID. Đây chính là sức mạnh của ReAct: môi trường (TMDB API) giữ state thay cho context window của LLM, giảm hallucination theo cấp số nhân với số bước.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Chuyển tool execution sang `asyncio` thay `ThreadPoolExecutor` để xử lý nhiều yêu cầu đồng thời mà không block. Thêm vector DB (Chroma, Qdrant) để retrieval tool phù hợp khi số lượng tool vượt ~20, tránh làm đầy context window bằng toàn bộ tool spec.

- **Safety**: Thêm Supervisor LLM kiểm tra output của agent trước khi trả về user — phát hiện hallucination còn sót, nội dung không phù hợp, hoặc final answer không liên quan đến câu hỏi. Validate mood/genre input bằng whitelist ở tầng API, không chỉ ở tầng tool.

- **Performance**: Cache kết quả TMDB theo `movie_id` và TTL ngắn (5 phút) để tránh gọi API lặp lại trong cùng session. Implement prompt caching (Anthropic/OpenAI) cho system prompt cố định của agent để giảm prompt tokens khi max_steps lớn.
