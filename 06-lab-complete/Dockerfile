# ============================================================
# Streamlit Movie ReAct Agent - multi-stage production image
# ============================================================

FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt \
    && python -m pip uninstall -y pytest iniconfig pluggy >/dev/null 2>&1 || true \
    && find /root/.local -type d \( -name tests -o -name test -o -name __pycache__ \) -prune -exec rm -rf {} + \
    && find /root/.local -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete


FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -m -r -g agent -d /home/agent agent

WORKDIR /app

COPY --from=builder /root/.local /home/agent/.local
COPY src/ ./src/
COPY .env.example ./.env.example

RUN chown -R agent:agent /app

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('PORT', '8501'); urllib.request.urlopen(f'http://localhost:{port}/_stcore/health')" || exit 1

CMD ["sh", "-c", "streamlit run src/app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true --browser.gatherUsageStats=false"]
