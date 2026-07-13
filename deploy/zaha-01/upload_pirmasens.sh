#!/usr/bin/env bash
# Sync Pirmasens cache + code to zaha-01, rebuild demo, smoke-test.
# Run from repo root: bash deploy/zaha-01/upload_pirmasens.sh
set -euo pipefail

REMOTE="${MARIECP_REMOTE:-xz378@zaha-01}"
REMOTE_REPO="${MARIECP_REMOTE_REPO:-/home/xz378/mariecp}"
REMOTE_DATA="${MARIECP_REMOTE_DATA:-/home/xz378/mini_marie_data/data}"
LOCAL_DATA="${MINI_MARIE_DATA_DIR:-D:/mini_marie_data/data}"

if command -v cygpath >/dev/null 2>&1 && [[ "${LOCAL_DATA}" == [A-Za-z]:* ]]; then
  LOCAL_DATA="$(cygpath -u "${LOCAL_DATA}")"
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ONTOP_DB="${LOCAL_DATA}/mini_marie_cache/twa_city/pirmasens_ontop_cache.sqlite"

WARM_MODE="${PIRMASENS_WARM_MODE:-page-questions}"
SKIP_BUILD="${PIRMASENS_SKIP_BUILD:-0}"

if [[ "${WARM_MODE}" != "remote-warm" && "${WARM_MODE}" != "full-fast" && ! -f "${ONTOP_DB}" ]]; then
  echo "ERROR: missing ${ONTOP_DB} — run warm_pirmasens_ontop_cache --page-questions first" >&2
  exit 1
fi

if [[ "${WARM_MODE}" != "remote-warm" && "${WARM_MODE}" != "full-fast" ]]; then
  echo "==> Upload pirmasens_ontop_cache.sqlite"
  rsync -avP "${ONTOP_DB}" "${REMOTE}:${REMOTE_DATA}/mini_marie_cache/twa_city/"
fi

echo "==> Sync Pirmasens code paths"
rsync -avP \
  "${ROOT}/mini_marie/zaha/twa_city/pirmasens_ontop_cache.py" \
  "${ROOT}/mini_marie/zaha/twa_city/pirmasens_ontop_operations.py" \
  "${ROOT}/mini_marie/zaha/twa_city/pirmasens_md_sparql.py" \
  "${ROOT}/mini_marie/zaha/twa_city/warm_pirmasens_ontop_cache.py" \
  "${ROOT}/mini_marie/zaha/twa_city/pirmasens_operations.py" \
  "${ROOT}/mini_marie/zaha/twa_city/main.py" \
  "${ROOT}/mini_marie/zaha/twa_city/test_pirmasens_ontop_cache.py" \
  "${REMOTE}:${REMOTE_REPO}/mini_marie/zaha/twa_city/"

rsync -avP \
  "${ROOT}/mini_marie/kg_catalog/catalog.py" \
  "${REMOTE}:${REMOTE_REPO}/mini_marie/kg_catalog/"

rsync -avP \
  "${ROOT}/mini_marie/kgqa/agent.py" \
  "${REMOTE}:${REMOTE_REPO}/mini_marie/kgqa/"

rsync -avP \
  "${ROOT}/mini_marie/zaha/twa_city/workflows/pirmasens_ubem_ranked.json" \
  "${ROOT}/mini_marie/zaha/twa_city/workflows/pirmasens_ubem_co2_ranked.json" \
  "${ROOT}/mini_marie/zaha/twa_city/workflows/pirmasens_ubem_heat_filter.json" \
  "${ROOT}/mini_marie/zaha/twa_city/sparql_plans.py" \
  "${ROOT}/mini_marie/zaha/twa_city/workflow_engine.py" \
  "${ROOT}/mini_marie/zaha/twa_city/workflow_mcp.py" \
  "${REMOTE}:${REMOTE_REPO}/mini_marie/zaha/twa_city/"

rsync -avP \
  "${ROOT}/mini_marie/zaha/twa_city/workflows/pirmasens_ubem_ranked.json" \
  "${ROOT}/mini_marie/zaha/twa_city/workflows/pirmasens_ubem_co2_ranked.json" \
  "${ROOT}/mini_marie/zaha/twa_city/workflows/pirmasens_ubem_heat_filter.json" \
  "${REMOTE}:${REMOTE_REPO}/mini_marie/zaha/twa_city/workflows/"

rsync -avP \
  "${ROOT}/demos/german_city_competency_questions.json" \
  "${ROOT}/demos/german_city_specs.py" \
  "${ROOT}/demos/twa_adapter.py" \
  "${ROOT}/demos/warm_german_city_caches.py" \
  "${ROOT}/demos/test_german_city_mcp_e2e.py" \
  "${ROOT}/demos/test_german_city_cache_alignment.py" \
  "${ROOT}/demos/test_german_city_specs.py" \
  "${ROOT}/demos/test_pirmasens_md_cqs.py" \
  "${REMOTE}:${REMOTE_REPO}/demos/"

rsync -avP \
  "${ROOT}/demos/marie-classic/static/data/german_city_competency_questions.json" \
  "${REMOTE}:${REMOTE_REPO}/demos/marie-classic/static/data/" 2>/dev/null || true

rsync -avP \
  "${ROOT}/demos/marie-classic/static/js/german_city_questions.js" \
  "${REMOTE}:${REMOTE_REPO}/demos/marie-classic/static/js/" 2>/dev/null || true

if [[ "${WARM_MODE}" == "full-fast" ]]; then
  ONTOP_WARM_FLAGS="--full-fast --missing-only"
elif [[ "${WARM_MODE}" == "remote-warm" ]]; then
  ONTOP_WARM_FLAGS="--full-fast --missing-only"
else
  ONTOP_WARM_FLAGS="--page-questions --missing-only"
fi

BUILD_FLAG="--build"
if [[ "${SKIP_BUILD}" == "1" ]]; then
  BUILD_FLAG=""
fi

echo "==> Restart mariecp-demo (warm_mode=${WARM_MODE}, skip_build=${SKIP_BUILD})"
ssh "${REMOTE}" bash -lc "'
  set -e
  cd \"${REMOTE_REPO}\"
  if [[ -n \"${BUILD_FLAG}\" ]]; then
    docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo up -d ${BUILD_FLAG}
    echo Waiting for health...
    for i in 1 2 3 4 5 6 7 8 9 10; do
      if curl -sf http://127.0.0.1:3001/health >/dev/null; then break; fi
      sleep 3
    done
  else
    docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo up -d
  fi
  docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo exec -T mariecp-demo \
    python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache ${ONTOP_WARM_FLAGS}
  docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo exec -T mariecp-demo \
    python -m mini_marie.zaha.twa_city.warm_city_cache --city pirmasens --atomics-only --missing-only
  docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo exec -T mariecp-demo \
    python -m mini_marie.zaha.twa_city.warm_city_cache --city pirmasens --locations-only --locations-top-n 12 --missing-only
  docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo exec -T mariecp-demo \
    python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --status
  docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo exec -T mariecp-demo \
    python -c \"from mini_marie.zaha.twa_city.pirmasens_ontop_operations import run_sparql_on_endpoint; rows=run_sparql_on_endpoint('"'"'toilet'"'"', '"'"'PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/> SELECT ?toilet WHERE { ?toilet a obe:Toilet . }'"'"', limit=5); print('"'"'cache_toilets'"'"', len(rows), rows[0] if rows else None)\"
  docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo exec -T mariecp-demo \
    python -m mini_marie.zaha.twa_city.city_cache_status --city pirmasens
'"

echo "Done."
