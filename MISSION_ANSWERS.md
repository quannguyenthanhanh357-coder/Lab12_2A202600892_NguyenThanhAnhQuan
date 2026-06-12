# Day 12 Lab - Mission Answers

Student: Nguyen Thanh Anh Quan  
Student ID: 2A202600892  
Final lab app: Streamlit Movie ReAct Agent from `anhtrinh2905/react-agent-recommend-movie`

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. Hardcoded API keys are unsafe because they can leak through GitHub, screenshots, logs, or Docker layers.
2. Local-only commands such as `streamlit run src/app.py` do not automatically become production-ready without a fixed host, dynamic port, and health check.
3. Installing dev/test dependencies in the runtime image increases image size and deploy time.
4. Running the app as root inside Docker is unnecessary risk.
5. Depending on local `.env` files breaks cloud deployment because Railway/Render use environment variables.
6. Missing health checks makes it harder for Docker or Railway to know whether the container is ready.
7. Using local-only model/provider assumptions can fail in production if the required key is not configured.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
| --- | --- | --- | --- |
| Config | `.env` file on laptop | Railway/Render environment variables | Keeps secrets out of the repo and lets cloud services inject config |
| Port | Usually fixed `8501` | Dynamic `${PORT:-8501}` | Cloud platforms assign the public runtime port |
| Host binding | `localhost` | `0.0.0.0` | Allows traffic from outside the container |
| Secrets | Manual local keys | `OPENAI_API_KEY`, `TMDB_API_KEY`, etc. in platform variables | Prevents accidental commits and supports key rotation |
| Health | Browser check | `/_stcore/health` endpoint | Lets Docker/Railway verify the container is alive |
| Runtime user | Often default/root | Non-root `agent` user | Reduces production container risk |
| Image contents | Source, tests, cache, dev tools | Multi-stage image with only runtime files | Smaller image and faster deployment |
| Logs | Local terminal | Platform logs | Required for debugging deployed containers |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11-slim`.
2. Build approach: multi-stage Dockerfile with a `builder` stage for dependency installation and a smaller runtime stage for execution.
3. Working directory: `/app`.
4. App user: non-root user named `agent`.
5. Runtime command: Streamlit starts with `--server.address=0.0.0.0` and `--server.port=${PORT:-8501}`.
6. Health check: Docker checks `http://127.0.0.1:${PORT:-8501}/_stcore/health`.
7. Optimization: `.dockerignore` and builder cleanup remove caches, tests, and bytecode from the runtime image.

### Exercise 2.3: Image size comparison

- Development-style image: larger because it can include build cache, tests, virtualenv files, and dev dependencies.
- Production Docker image: about 155 MB by Docker inspect content size, under the 500 MB requirement.
- Docker Desktop disk usage can look larger because it shows uncompressed/layer storage, but the production content size is still within the lab target.
- Main optimization choices: slim Python base image, multi-stage build, non-root runtime, and dependency/cache cleanup.

### Local Docker verification

```bash
cd 06-lab-complete
docker compose up -d --build --remove-orphans
curl http://localhost:8501/_stcore/health
# Expected: ok

curl -I http://localhost:8501/
# Expected: HTTP 200 with text/html
```

Result: local Docker container built successfully, became healthy, and served the Streamlit UI on `localhost:8501`.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- Public URL: https://agent-production-be3d.up.railway.app
- Platform: Railway
- Service: `agent`
- Health path: `/_stcore/health`
- Final deployment target: `06-lab-complete` Streamlit Movie ReAct Agent.

Verification:

```bash
curl https://agent-production-be3d.up.railway.app/_stcore/health
# ok

curl -I https://agent-production-be3d.up.railway.app/
# HTTP 200, content-type text/html
```

Required Railway variables:

- `PORT`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `GEMINI_API_KEY`
- `TMDB_API_KEY`
- `DEFAULT_PROVIDER`
- `DEFAULT_MODEL`
- `TMDB_LANGUAGE`
- `TMDB_REGION`
- `LOG_LEVEL`

No real secret values are committed to the repository.

## Part 4: API Security

### Exercise 4.1-4.3: Test results

The original Day 12 checklist describes an API service with `/ask`, API-key authentication, rate limiting, and cost guard endpoints. The final lab artifact was changed to the requested movie recommendation repo, which is a Streamlit UI app rather than a public REST API.

Because of that, the production checks for the final app are:

```bash
curl https://agent-production-be3d.up.railway.app/_stcore/health
# Expected: ok

curl -I https://agent-production-be3d.up.railway.app/
# Expected: HTTP 200 text/html
```

Security controls used in the final Streamlit deployment:

1. API keys are read only from environment variables.
2. `.env` is not committed; only `.env.example` is kept.
3. Docker image does not contain hardcoded OpenAI/TMDB keys.
4. Runtime container uses a non-root user.
5. The public surface is the Streamlit web UI, not an unauthenticated `/ask` REST endpoint.

### Exercise 4.4: Cost guard implementation

For the final Streamlit Movie ReAct Agent, cost control is handled through deployment configuration and agent guardrails:

- Default model is set to `gpt-4o-mini` to reduce cost.
- The ReAct loop has a maximum step count to avoid infinite tool/model calls.
- Provider keys are environment variables, so they can be rotated immediately if exposed.
- Optional providers can be disabled by not setting their keys.

In the original FastAPI version of this lab, API-key authentication, rate limiting, and monthly budget tracking were implemented for `/ask`. After switching lab 6 to the movie repo, the final deployment no longer exposes that REST API path.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

- Liveness: Streamlit exposes `/_stcore/health`, and both Docker and Railway use it.
- Readiness: the container is considered ready once Streamlit starts and the health endpoint returns `ok`.
- Stateless deployment: app configuration comes from environment variables; no local `.env` is required in production.
- Provider abstraction: the movie app supports OpenAI, DeepSeek, Gemini, and local/provider-specific options through config.
- Reliability: Railway restarts failed containers automatically, and the Docker health check detects unhealthy containers.
- Observability: Railway logs show Streamlit startup, bound port, and runtime messages.
- Rollback: changes are versioned in GitHub and redeployed through Railway.

## Final Submission Summary

- GitHub repository: `quannguyenthanhanh357-coder/Lab12_2A202600892_NguyenThanhAnhQuan`
- Final deploy folder: `06-lab-complete`
- Public service: https://agent-production-be3d.up.railway.app
- Local Docker: verified on `http://localhost:8501`
- Cloud health: verified with `/_stcore/health`
- Code tests: `python -m compileall .\src .\tests` passed; `pytest -q` passed with one optional local-LLM test skipped.
