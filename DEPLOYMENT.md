# Deployment Information

## Public URL

TBD - deploy with your Railway, Render, or Cloud Run account and replace this line with the public service URL.

## Platform

Railway or Render.

## Test Commands

Set these first:

```bash
export URL=https://your-agent.example.com
export KEY=your-production-api-key
```

### Health Check

```bash
curl $URL/health
# Expected: {"status":"ok", ...}
```

### Readiness Check

```bash
curl $URL/ready
# Expected: {"ready":true,"redis":true}
```

### API Test With Authentication

```bash
curl -X POST $URL/ask \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

### Authentication Required

```bash
curl -X POST $URL/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: 401
```

### Rate Limiting

```bash
for i in {1..15}; do
  curl -X POST $URL/ask \
    -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test","question":"rate limit test"}'
done
# Expected: eventually returns 429
```

## Environment Variables Set

- `PORT`
- `ENVIRONMENT=production`
- `REDIS_URL`
- `AGENT_API_KEY`
- `JWT_SECRET`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10.0`
- `LOG_LEVEL=INFO`

## Screenshots

- `screenshots/dashboard.png` - add after deployment
- `screenshots/running.png` - add after deployment
- `screenshots/test.png` - add after deployment
