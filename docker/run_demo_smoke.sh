#!/usr/bin/env bash
# Build + start demo container and run smoke tests.
#
# Usage (repo root):
#   MARIECP_DATA=/path/to/mini_marie_data/data bash docker/run_demo_smoke.sh
#   MARIECP_DATA=D:/mini_marie_data/data bash docker/run_demo_smoke.sh   # Git Bash
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

COMPOSE=(docker compose --env-file configs/demo_docker.env --env-file configs/demo_publish.env -f docker/compose.demo.yml -p mariecp-demo)
PORT="${MARIECP_PORT:-3001}"
PUBLISH_HOST="${MARIECP_PUBLISH_HOST:-0.0.0.0}"
DATA="${MARIECP_DATA:-}"

if [[ -z "${DATA}" ]]; then
  for candidate in \
    "D:/mini_marie_data/data" \
    "/mnt/d/mini_marie_data/data" \
    "${HOME}/mini_marie_data/data" \
    "./data"; do
    if [[ -d "${candidate}/mini_marie_cache/chemistry" ]]; then
      DATA="${candidate}"
      break
    fi
  done
fi

if [[ -z "${DATA}" ]]; then
  echo "WARN: MARIECP_DATA not set and no warmed cache found — cache API tests may fail" >&2
  DATA="./data"
fi

export MARIECP_DATA="${DATA}"
export MARIECP_PORT="${PORT}"
export MARIECP_PUBLISH_HOST="${PUBLISH_HOST}"

echo "==> Publish: ${PUBLISH_HOST}:${PORT} -> container :8080"
echo "==> Cache mount: ${MARIECP_DATA} -> /data"
echo "==> Building image"
"${COMPOSE[@]}" build

echo "==> Starting container"
"${COMPOSE[@]}" up -d

cleanup() {
  "${COMPOSE[@]}" logs --tail=40 mariecp-demo 2>/dev/null || true
}
trap cleanup ERR

deadline=$((SECONDS + 120))
until curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; do
  if (( SECONDS > deadline )); then
    echo "ERROR: container did not become healthy in time" >&2
    "${COMPOSE[@]}" logs mariecp-demo
    exit 1
  fi
  sleep 2
done
echo "==> Health OK"

echo "==> Hub smoke (in container)"
"${COMPOSE[@]}" exec -T mariecp-demo python -m demos.test_server_hub

if [[ -f "${MARIECP_DATA}/mini_marie_cache/chemistry/chemistry_cache.sqlite" ]]; then
  echo "==> Cache + search API smoke (in container)"
  "${COMPOSE[@]}" exec -T mariecp-demo python -m demos.test_demo_setup
else
  echo "==> Skipping cache tests (no chemistry_cache.sqlite under ${MARIECP_DATA})"
fi

echo "==> HTTP checks"
curl -sf "http://127.0.0.1:${PORT}/demos/hub/" | head -c 200
echo ""
curl -sf "http://127.0.0.1:${PORT}/health/cache" | python3 -m json.tool 2>/dev/null | head -20 || true

echo ""
echo "Demo Docker smoke passed. Container still running:"
echo "  ${COMPOSE[*]} logs -f"
echo "  ${COMPOSE[*]} down    # stop only this project"
