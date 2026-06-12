# Lab 6 Complete - Streamlit Movie ReAct Agent Deployment

This folder contains the final deployment target for the Day 12 cloud deployment lab.

The app is the requested Movie ReAct Agent from:

```text
https://github.com/anhtrinh2905/react-agent-recommend-movie
```

It is packaged with Docker and deployed on Railway as a production Streamlit app.

## What This App Does

- Recommends movies through a ReAct-style agent loop.
- Uses TMDB tools for live movie search, details, trending movies, similar movies, streaming availability, and comparisons.
- Supports multiple LLM providers through environment variables.
- Runs as a Streamlit UI rather than a REST `/ask` API.

## Production Checklist

- [x] Multi-stage Dockerfile
- [x] Production image under the 500 MB lab requirement by Docker inspect content size
- [x] `.dockerignore` configured
- [x] Non-root runtime user
- [x] Dynamic cloud port support with `${PORT:-8501}`
- [x] Streamlit health endpoint: `/_stcore/health`
- [x] Railway config in `railway.toml`
- [x] Render config in `render.yaml`
- [x] No hardcoded secrets
- [x] Environment-based provider and TMDB configuration
- [x] Local Docker test passed
- [x] Railway public deployment verified

## Folder Structure

```text
06-lab-complete/
├── src/                   # Streamlit UI, ReAct agent, tools, providers
├── tests/                 # Project tests
├── report/                # Lab report files from the movie agent project
├── Dockerfile             # Multi-stage production Docker build
├── docker-compose.yml     # Local Docker run configuration
├── railway.toml           # Railway deployment config
├── render.yaml            # Render deployment config
├── requirements.txt       # Production dependencies
├── requirements-local.txt # Optional local model dependencies
├── .env.example           # Environment template only
└── .dockerignore          # Files excluded from Docker build context
```

## Environment Variables

Create `.env` locally from `.env.example`, or set these in Railway:

```text
OPENAI_API_KEY=YOUR_OPENAI_KEY
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_KEY
GEMINI_API_KEY=YOUR_GEMINI_KEY
TMDB_API_KEY=YOUR_TMDB_KEY
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini
TMDB_LANGUAGE=vi-VN
TMDB_REGION=VN
LOG_LEVEL=INFO
```

Do not commit `.env` or real API keys.

## Run Locally With Docker

```bash
cd 06-lab-complete
docker compose up -d --build --remove-orphans
```

Open:

```text
http://localhost:8501
```

Health check:

```bash
curl http://localhost:8501/_stcore/health
# Expected: ok
```

Check root page:

```bash
curl -I http://localhost:8501/
# Expected: HTTP 200 and content-type text/html
```

## Run Locally Without Docker

```bash
cd 06-lab-complete
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run src/app.py --server.port=8501
```

Open:

```text
http://localhost:8501
```

## Deploy To Railway

Install and login:

```powershell
npm install -g @railway/cli
railway.cmd login
```

Set variables with placeholder values:

```powershell
railway.cmd variable set OPENAI_API_KEY="YOUR_OPENAI_KEY" --service agent
railway.cmd variable set TMDB_API_KEY="YOUR_TMDB_KEY" --service agent
railway.cmd variable set DEFAULT_PROVIDER="openai" --service agent
railway.cmd variable set DEFAULT_MODEL="gpt-4o-mini" --service agent
railway.cmd variable set TMDB_LANGUAGE="vi-VN" --service agent
railway.cmd variable set TMDB_REGION="VN" --service agent
railway.cmd variable set LOG_LEVEL="INFO" --service agent
```

Deploy:

```powershell
railway.cmd up --service agent
```

Production URL:

```text
https://agent-production-be3d.up.railway.app
```

Production health:

```powershell
curl https://agent-production-be3d.up.railway.app/_stcore/health
# Expected: ok
```

## Verification Results

Commands verified for the final submission:

```powershell
python -m compileall .\src .\tests
# Passed

pytest -q
# Passed with one optional local-LLM test skipped when llama_cpp is not installed

docker compose up -d --build --remove-orphans
# Container became healthy

curl http://localhost:8501/_stcore/health
# ok

curl https://agent-production-be3d.up.railway.app/_stcore/health
# ok
```

## Notes About The Original Day 12 API Checklist

The original Day 12 lab template mentions `/health`, `/ready`, `/ask`, API-key authentication, rate limiting, Redis state, and cost guard for a FastAPI agent service.

For this submission, Lab 6 was intentionally changed to deploy the requested Streamlit Movie ReAct Agent repository. Therefore:

- The app health endpoint is `/_stcore/health`.
- The user-facing entry point is `/`.
- There is no public `/ask` REST endpoint in the final deployed app.
- Secrets are still protected through environment variables.
- Cost is reduced through `gpt-4o-mini`, provider configuration, and max-step agent guardrails.
