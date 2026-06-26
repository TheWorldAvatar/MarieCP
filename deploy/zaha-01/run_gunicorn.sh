#!/usr/bin/env bash
# Gunicorn launcher for systemd — prefers repo-local conda env over .venv.
set -euo pipefail

ROOT="${MARIECP_DIR:-/home/xz378/mariecp}"
cd "${ROOT}"

BIND="${MARIECP_BIND:-127.0.0.1:8080}"
WORKERS="${MARIECP_WORKERS:-2}"
TIMEOUT="${MARIECP_TIMEOUT:-300}"

if [[ -x "${ROOT}/.conda-env/bin/gunicorn" ]]; then
  GUNICORN="${ROOT}/.conda-env/bin/gunicorn"
elif [[ -x "${ROOT}/.venv/bin/gunicorn" ]]; then
  GUNICORN="${ROOT}/.venv/bin/gunicorn"
else
  echo "ERROR: no gunicorn in ${ROOT}/.conda-env or ${ROOT}/.venv" >&2
  exit 1
fi

exec "${GUNICORN}" -w "${WORKERS}" -b "${BIND}" --timeout "${TIMEOUT}" \
  --access-logfile - --error-logfile - \
  demos.server:app
