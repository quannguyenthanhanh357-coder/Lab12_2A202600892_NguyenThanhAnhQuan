# Deployment Information

## Public URL

https://agent-production-be3d.up.railway.app

## Platform

Railway

## Test Commands

Set these first:

```bash
export URL=https://agent-production-be3d.up.railway.app
```

### Health Check

```bash
curl $URL/_stcore/health
# Expected: ok
```

### App Page

```bash
curl -I $URL/
# Expected: HTTP 200 text/html
```

### Manual UI Test

Open `$URL` in a browser. The Streamlit Movie ReAct Agent should load and show model/tool configuration in the sidebar.

## Environment Variables Set

- `PORT`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `GEMINI_API_KEY`
- `TMDB_API_KEY`
- `DEFAULT_MODEL=gpt-4o-mini`
- `LOG_LEVEL=INFO`

## Screenshots

- `screenshots/dashboard.png` - Railway dashboard
- `screenshots/deploy.png` - deployed public service
- `screenshots/docker-local.png` - local Docker image/container evidence
- `screenshots/log-railway.png` - Railway runtime logs
