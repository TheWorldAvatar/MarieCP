#!/usr/bin/env bash
# Deploy MarieCP demos on zaha-01 via Docker Compose (isolated project).
#
# Safe alongside other Docker stacks:
#   - project name: mariecp-demo (never touches other compose projects)
#   - publishes 0.0.0.0:3001 -> container :8080 (external access)
#   - no apt, no system Python, no nginx reload
#
# Usage:
#   bash deploy/zaha-01/install.sh
#
# Optional:
#   MARIECP_DATA=/home/xz378/mini_marie_data/data
#   MARIECP_PORT=3001
#   MARIECP_PUBLISH_HOST=0.0.0.0
#   SKIP_BUILD=1
#
set -euo pipefail

REPO_DIR="${MARIECP_DIR:-/home/xz378/mariecp}"
REPO_URL="${MARIECP_REPO:-https://github.com/TheWorldAvatar/MarieCP.git}"
BRANCH="${MARIECP_BRANCH:-main}"
DATA_DIR="${MARIECP_DATA:-${MINI_MARIE_DATA_DIR:-/home/xz378/mini_marie_data/data}}"
BIND_PORT="${MARIECP_PORT:-3001}"
PUBLISH_HOST="${MARIECP_PUBLISH_HOST:-0.0.0.0}"
COMPOSE=(docker compose --env-file configs/demo_docker.env --env-file configs/demo_publish.env -f docker/compose.demo.yml -p mariecp-demo)

echo "==> MarieCP demo install (Docker)"
echo "    repo:    ${REPO_DIR} (${BRANCH})"
echo "    caches:  ${DATA_DIR}/mini_marie_cache"
echo "    publish: ${PUBLISH_HOST}:${BIND_PORT} -> container :8080"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found" >&2
  exit 1
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  git clone --branch "${BRANCH}" "${REPO_URL}" "${REPO_DIR}"
else
  git -C "${REPO_DIR}" fetch origin
  git -C "${REPO_DIR}" checkout "${BRANCH}"
  git -C "${REPO_DIR}" pull --ff-only origin "${BRANCH}"
fi

cd "${REPO_DIR}"

if [[ ! -f .env ]]; then
  echo "==> Creating .env stub — set REMOTE_API_KEY for QA/chat"
  cat > .env <<'EOF'
REMOTE_BASE_URL=https://openrouter.ai/api/v1
REMOTE_API_KEY=REPLACE_ME
DEMO_LLM_MODEL=gpt-4o
FLASK_SECRET_KEY=change-me-in-production
EOF
fi

# shellcheck disable=SC1091
if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env 2>/dev/null || echo "WARN: could not source .env — fix syntax or set REMOTE_API_KEY in environment" >&2
  set +a
fi
export REMOTE_BASE_URL="${REMOTE_BASE_URL:-https://openrouter.ai/api/v1}"
export REMOTE_API_KEY="${REMOTE_API_KEY:-REPLACE_ME}"
export DEMO_LLM_MODEL="${DEMO_LLM_MODEL:-gpt-4o}"
export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-change-me-in-production}"

echo "==> Cache layout"
missing=0
for name in sg_old chemistry twa_city; do
  sub="${DATA_DIR}/mini_marie_cache/${name}"
  db="$(find "${sub}" -name '*.sqlite' -print -quit 2>/dev/null || true)"
  if [[ -n "${db}" ]]; then
    echo "  OK  ${name}: ${db}"
  else
    echo "  MISSING ${name} under ${sub}"
    missing=1
  fi
done
if [[ "${missing}" -eq 1 ]]; then
  echo "Upload caches first: bash deploy/zaha-01/upload_caches.sh (from dev machine)" >&2
  exit 1
fi

export MARIECP_DATA="${DATA_DIR}"
export MARIECP_PORT="${BIND_PORT}"
export MARIECP_PUBLISH_HOST="${PUBLISH_HOST}"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "==> docker compose build (project mariecp-demo only)"
  "${COMPOSE[@]}" build
fi

echo "==> docker compose up -d"
"${COMPOSE[@]}" up -d

deadline=$((SECONDS + 180))
until curl -sf "http://127.0.0.1:${BIND_PORT}/health" >/dev/null 2>&1; do
  if (( SECONDS > deadline )); then
    echo "ERROR: health check timed out" >&2
    "${COMPOSE[@]}" logs --tail=80 mariecp-demo
    exit 1
  fi
  sleep 2
done

echo "==> In-container smoke"
"${COMPOSE[@]}" exec -T mariecp-demo python -m demos.test_server_hub
"${COMPOSE[@]}" exec -T mariecp-demo python -m demos.test_demo_setup

curl -sf "http://127.0.0.1:${BIND_PORT}/health" && echo "  health OK"
curl -sf "http://127.0.0.1:${BIND_PORT}/demos/hub/" >/dev/null && echo "  hub OK"

cat <<EOF

Deployed. Only stack 'mariecp-demo' was started/restarted.

Manage:
  cd ${REPO_DIR}
  docker compose -f docker/compose.demo.yml -p mariecp-demo ps
  docker compose -f docker/compose.demo.yml -p mariecp-demo logs -f
  docker compose -f docker/compose.demo.yml -p mariecp-demo up -d --build   # upgrade

Next: merge deploy/zaha-01/nginx-mariecp-demo.conf on www.theworldavatar.io
      (upstream 127.0.0.1:${BIND_PORT})

EOF
