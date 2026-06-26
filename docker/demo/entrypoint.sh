#!/usr/bin/env bash
set -euo pipefail

cd /app

if [[ "${DEMO_MIRROR_ON_START:-1}" == "1" ]]; then
  if [[ ! -f demos/static/zaha/index.html ]]; then
    echo "==> Mirroring Zaha static assets from theworldavatar.io"
    python -m demos.mirror || echo "WARN: mirror failed; Zaha UI may be incomplete" >&2
  fi
fi

WORKERS="${MARIECP_WORKERS:-2}"
TIMEOUT="${MARIECP_TIMEOUT:-300}"
BIND="${DEMO_HOST:-0.0.0.0}:${DEMO_PORT:-8080}"

exec gunicorn -w "${WORKERS}" -b "${BIND}" --timeout "${TIMEOUT}" \
  --access-logfile - --error-logfile - \
  demos.server:app
