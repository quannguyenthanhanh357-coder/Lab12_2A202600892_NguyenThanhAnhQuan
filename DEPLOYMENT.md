# Deployment Information

## Public URL

https://agent-production-be3d.up.railway.app

## Platform

Railway

## Application

Streamlit Movie ReAct Agent deployed from `06-lab-complete`.

Source app requested for Lab 6 deployment:

```text
https://github.com/anhtrinh2905/react-agent-recommend-movie
```

## Test Commands

Set the public URL first:

```bash
export URL=https://agent-production-be3d.up.railway.app
```

PowerShell equivalent:

```powershell
$env:URL = "https://agent-production-be3d.up.railway.app"
```

### Health Check

```bash
curl $URL/_stcore/health
# Expected: ok
```

PowerShell:

```powershell
curl "$env:URL/_stcore/health"
# Expected: ok
```

### App Page

```bash
curl -I $URL/
# Expected: HTTP 200 and content-type text/html
```

PowerShell:

```powershell
curl -I "$env:URL/"
# Expected: HTTP 200 and content-type text/html
```

### Local Docker Test

```bash
cd 06-lab-complete
docker compose up -d --build --remove-orphans
curl http://localhost:8501/_stcore/health
# Expected: ok

curl -I http://localhost:8501/
# Expected: HTTP 200 and content-type text/html
```

## Environment Variables Set

No real secret values are stored in GitHub.

- `PORT`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `GEMINI_API_KEY`
- `TMDB_API_KEY`
- `DEFAULT_PROVIDER`
- `DEFAULT_MODEL=gpt-4o-mini`
- `TMDB_LANGUAGE=vi-VN`
- `TMDB_REGION=VN`
- `LOG_LEVEL=INFO`

Railway setup commands use placeholder values:

```powershell
railway.cmd variable set OPENAI_API_KEY="YOUR_OPENAI_KEY" --service agent
railway.cmd variable set TMDB_API_KEY="YOUR_TMDB_KEY" --service agent
railway.cmd variable set DEFAULT_PROVIDER="openai" --service agent
railway.cmd variable set DEFAULT_MODEL="gpt-4o-mini" --service agent
railway.cmd variable set TMDB_LANGUAGE="vi-VN" --service agent
railway.cmd variable set TMDB_REGION="VN" --service agent
railway.cmd variable set LOG_LEVEL="INFO" --service agent
```

## Deployment Commands

```powershell
cd C:\Users\ADMIN\Desktop\day12_ha-tang-cloud_va_deployment\06-lab-complete
railway.cmd up --service agent
```

Railway deployment result verified:

- Deployment status: success
- Runtime log: Streamlit starts on `0.0.0.0:$PORT`
- Health endpoint: `/_stcore/health` returns `ok`
- Public root page: `/` returns `HTTP 200`

## Screenshots To Include

Place screenshots in the repository `screenshots/` folder before final submission:

- `screenshots/dashboard.png` - Railway dashboard showing the deployed service
- `screenshots/deploy.png` - public Streamlit app running in browser
- `screenshots/docker-local.png` - Docker Desktop or terminal showing healthy local container
- `screenshots/log-railway.png` - Railway logs showing Streamlit startup

## Notes

The original Day 12 checklist includes REST API tests for `/health`, `/ready`, and `/ask`. The final Lab 6 app was changed to the requested Streamlit Movie ReAct Agent, so the correct production health endpoint is Streamlit's `/_stcore/health`.
