# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. Hardcoded secrets and default credentials are unsafe in production.
2. In-memory state breaks when the app runs on multiple instances.
3. Missing health and readiness checks makes cloud orchestration unreliable.
4. Running without authentication exposes the agent to public abuse.
5. No rate limit or budget guard can cause denial of service or unexpected LLM cost.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
| --- | --- | --- | --- |
| Config | Local defaults | Environment variables | Keeps secrets out of code and supports cloud platforms |
| Secrets | Demo values | Required external values | Prevents leaked API keys |
| State | In memory | Redis | Enables horizontal scaling |
| Auth | Optional or demo | Required API key | Protects public endpoints |
| Observability | Plain logs | Structured JSON logs | Easier monitoring and debugging |
| Reliability | Manual testing | Health and readiness probes | Lets platforms restart or drain unhealthy containers |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11-slim`.
2. Working directory: `/app` in runtime and `/build` in builder.
3. Multi-stage build: dependencies are installed in a builder stage, then copied into a smaller runtime stage.
4. Non-root user: the container runs as `agent`.
5. Health check: Docker calls `/health` inside the container.

### Exercise 2.3: Image size comparison

- Develop: typically larger because it includes build tools and dev files.
- Production: expected to stay under 500 MB because it uses `python:3.11-slim`, `.dockerignore`, and a multi-stage build.
- Difference: production image should be significantly smaller and safer to deploy.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: update this after deployment in `DEPLOYMENT.md`.
- Platform config is included in `06-lab-complete/railway.toml`.
- Required variables: `ENVIRONMENT`, `AGENT_API_KEY`, `JWT_SECRET`, `REDIS_URL`, `RATE_LIMIT_PER_MINUTE`, `MONTHLY_BUDGET_USD`.

## Part 4: API Security

### Exercise 4.1-4.3: Test results

Expected results:

```bash
curl http://localhost:8000/ask
# 405 for GET or 401 when POST is sent without X-API-Key

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# 401 Invalid or missing API key

curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: local-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# 200 with answer
```

### Exercise 4.4: Cost guard implementation

The final app uses Redis to track monthly cost per API-key/user bucket. Before and after an LLM call, the service estimates cost from input and output tokens. If projected monthly spend is over `MONTHLY_BUDGET_USD` (default 10.0), the service returns `402`.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

- `/health` returns process liveness and basic dependency status.
- `/ready` returns 503 until Redis is reachable.
- `SIGTERM` marks the app not ready so load balancers can drain traffic.
- Rate limiting, cost usage, and conversation history are stored in Redis, not local memory.
- Docker Compose includes Redis so multiple agent containers can share state.
