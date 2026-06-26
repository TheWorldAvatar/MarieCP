# MarieCP TWA demo API (Marie classic + Zaha static + hub + KGQA)
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libgeos-c1v5 \
        libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt requirements-mini-marie.txt requirements-kgqa.txt requirements-demo.txt ./
RUN pip install --no-cache-dir -r requirements-demo.txt gunicorn

COPY mini_marie/ mini_marie/
COPY demos/ demos/
COPY configs/ configs/
COPY models/ models/
COPY src/ src/
COPY docker/demo/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p data/log raw_data sandbox/tasks sandbox/code data/generic

ENV PYTHONPATH=/app \
    DEMO_CONFIG=docker \
    MARIE_FRONTEND_PROXY=0 \
    DEMO_HOST=0.0.0.0 \
    DEMO_PORT=8080 \
    MINI_MARIE_DATA_DIR=/data

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -sf http://127.0.0.1:8080/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
