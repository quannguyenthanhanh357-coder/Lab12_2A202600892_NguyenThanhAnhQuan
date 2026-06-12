# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Trịnh Thị Lan Anh
- **Student ID**: 2A202600737
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

Trong lab này, tôi tập trung vào **tích hợp UI Streamlit**, **so sánh đa model**, và **mở rộng dữ liệu TMDB** để agent trả kết quả trực quan hơn.

- **Modules Implemented**:
  - `src/app.py` — giao diện chính: chế độ chat đơn, chế độ so sánh song song 2+ models, hiển thị poster phim từ trace, sidebar cấu hình agent/chatbot.
  - `src/ui/comparison.py` — chạy song song nhiều provider/model bằng `ThreadPoolExecutor`, render bảng metrics và biểu đồ latency.
  - `src/tools/tmdb_client.py` — bổ sung `poster_url`, `backdrop_url` vào response TMDB để UI render ảnh phim.
  - Sửa lỗi **session state** (`cmp_query`, `pending_prompt`) để câu hỏi gợi ý và chế độ so sánh hoạt động ổn định.

- **Code Highlights**:
  - Luồng so sánh song song: chọn `gpt-4o` và `gpt-4o-mini` → cùng một câu hỏi → `run_parallel_comparison()` gọi ReAct Agent v2 trên từng model → hiển thị cột kết quả + bảng latency/tokens.
  - Trích poster từ observation JSON trong trace (`extract_movies_from_trace`) rồi render grid bằng `render_movie_cards()`.
  - Đồng bộ widget Streamlit khi bấm gợi ý câu hỏi:
    ```python
    if pending:
        st.session_state.cmp_query = pending
        st.session_state.cmp_input = pending
    ```

- **Documentation — tương tác với ReAct loop**:
  1. User nhập câu hỏi trên UI → `run_query()` khởi tạo `ReActAgent` / `ReActAgentV2`.
  2. Agent sinh `Thought` → `Action: tool_name(args)` → `execute_tool()` trong `registry.py`.
  3. Observation (JSON từ TMDB) được đưa lại vào scratchpad cho bước tiếp theo.
  4. UI đọc `trace` và `metrics` từ kết quả để hiển thị trace panel, poster, và bảng so sánh model.

---

## II. Debugging Case Study (10 Points)

### Case 1: Agent lặp lỗi tool `search_movies`

- **Problem Description**: Khi hỏi *"Phim michael mới nhất"*, agent gọi `search_movies` liên tục 5 lần nhưng mỗi lần đều fail, hết `max_steps` mà không có câu trả lời hữu ích.

- **Log Source** (`logs/2026-06-01.log`, ~08:30):
  ```json
  {"event": "TOOL_CALL", "data": {"tool": "search_movies", "args": ["Michael", 1],
   "observation_preview": "{\"error\": \"Invalid arguments for search_movies: 'int' object is not subscriptable\"}"}}
  ```
  Lặp lại tương tự đến `AGENT_END` với `"steps": 5`.

- **Diagnosis**:
  - Lỗi nằm ở **tầng tool/client TMDB** (bug xử lý response), không phải do LLM gọi sai format argument.
  - Agent v1 **không có cơ chế recovery**: khi observation chứa `"error"`, model vẫn thử lại cùng tool thay vì đổi chiến lược.
  - Đây là minh chứng tại sao cần **Agent v2** với few-shot examples và error hint khi observation báo lỗi format/argument.

- **Solution**:
  - Sửa bug trong `tmdb_client.py` (xử lý genre_ids đúng kiểu dữ liệu).
  - Nâng cấp lên `ReActAgentV2`: thêm ví dụ đúng/sai trong system prompt, inject gợi ý format khi observation có `"Invalid arguments"`.
  - Sau fix, cùng loại câu hỏi search đã trả về danh sách phim hợp lệ (ví dụ `"Spirited Away"` → `get_movie_details(129)` thành công).

### Case 2: Câu hỏi gợi ý không điền được vào ô so sánh

- **Problem Description**: Bấm nút gợi ý ở sidebar nhưng ô *"Câu hỏi để so sánh"* vẫn trống; app crash với `AttributeError: st.session_state has no attribute "cmp_query"`.

- **Log Source**: Terminal Streamlit — `src/app.py`, line 192.

- **Diagnosis**:
  - `st.text_input(key="cmp_input")` quản lý state riêng; tham số `value=` chỉ có hiệu lực lần render đầu.
  - `cmp_query` chưa được khởi tạo trong `init_session()`.
  - Logic xử lý `pending_prompt` ở chế độ chat nằm ngoài `with col_chat`, nên không trigger đúng.

- **Solution**:
  - Khởi tạo `cmp_query = ""` và `cmp_results = None` trong `init_session()`.
  - Khi có `pending_prompt`, gán đồng thời `st.session_state.cmp_query` và `st.session_state.cmp_input`.
  - Gộp logic chat vào trong `with col_chat`.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning — vai trò của `Thought`**:
   - Với câu hỏi đa bước *"Tôi vừa xem Inception, gợi ý phim tương tự có trên Netflix"*, ReAct Agent v2 thể hiện chuỗi suy luận rõ ràng: `search_movies` → `get_similar_movies` → `check_streaming_availability` từng phim.
   - Khối `Thought` giúp agent **lập kế hoạch** trước khi gọi tool, thay vì trả lời một lần như Chatbot. Chatbot với cùng câu hỏi thường gợi ý phim dựa trên kiến thức nội tại, **không xác minh Netflix VN** qua TMDB.

2. **Reliability — Agent kém hơn Chatbot khi nào**:
   - **Câu hỏi đơn giản / ngoài phạm vi tool**: *"Thời lượng phim Spirited Away"* — Chatbot trả lời nhanh (~1.2s, 103 tokens). Agent mất 3 bước (search → search lại → get_details) tốn ~10s dù kết quả cuối chính xác hơn.
   - **Câu hỏi không liên quan phim**: *"Tôi là ai?"*, *"Hôm nay ăn gì?"* — Agent vẫn cố gắng dùng tool hoặc tốn bước suy luận không cần thiết; Chatbot từ chối/nhẹ nhàng hơn.
   - **Tool trả dữ liệu rỗng**: Netflix VN thường trả `"streaming": []` — agent tiếp tục gọi `check_streaming_availability` nhiều lần (5–7 steps), latency cao mà câu trả lời vẫn là *"không có trên Netflix"*.

3. **Observation — feedback ảnh hưởng bước tiếp theo**:
   - Khi `get_trending_movies("VN", "Animation", "week")` trả Super Mario 2026, agent chuyển sang `Final Answer` ngay — observation đủ để trả lời.
   - Khi `check_streaming_availability` trả mảng rỗng, agent thử phim tiếp theo trong danh sách similar — observation **điều hướng** hành vi sang tool khác thay vì hallucinate Netflix.
   - So sánh `gpt-4o` vs `gpt-4o-mini` (log 09:05–09:07): cả hai đều hoàn thành so sánh 3 phim Nolan, nhưng **gpt-4o-mini** dùng nhiều token hơn ở Chatbot mode (528 vs ~300 tokens) và đôi khi search với `limit=5` thay vì `limit=1`, tốn thêm 1 LLM call.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Dùng **async queue** (Celery / Redis) cho tool calls TMDB khi nhiều user so sánh model song song, tránh block Streamlit thread.
  - Cache response TMDB (Redis, TTL 1h) cho `search_movies` và `get_movie_details` — giảm quota API và latency.

- **Safety**:
  - Thêm **Supervisor LLM** kiểm tra `Action` trước khi execute (chặn gọi tool lặp vô hạn, câu hỏi ngoài domain).
  - Guardrail: nếu 2 observation liên tiếp cùng lỗi → buộc agent chuyển `Final Answer` với thông báo lỗi thân thiện.

- **Performance**:
  - Với hệ thống nhiều tool (>20), dùng **Vector DB** (embedding tool description) để retrieve top-k tool phù hợp thay vì nhét toàn bộ spec vào system prompt.
  - Streaming `Thought` + `Action` lên UI real-time để giảm cảm giác chờ khi agent chạy 5–7 bước.

---

> Báo cáo này dựa trên trace thực tế trong `logs/2026-06-01.log` và code tại `src/app.py`, `src/ui/comparison.py`, `src/agent/agent_v2.py`.
