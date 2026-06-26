#!/usr/bin/env bash
# Upload warmed SQLite caches from a dev machine to zaha-01.
# Run from repo root (Git Bash / WSL on Windows, or Linux).
#
# Usage:
#   bash deploy/zaha-01/upload_caches.sh
#   bash deploy/zaha-01/upload_caches.sh city          # twa_city only (~19 GB)
#   bash deploy/zaha-01/upload_caches.sh sg chemistry  # named subsets
#
set -euo pipefail

REMOTE="${MARIECP_REMOTE:-xz378@zaha-01}"
REMOTE_DATA="${MARIECP_REMOTE_DATA:-/home/xz378/mini_marie_data/data/mini_marie_cache}"
LOCAL_DATA="${MINI_MARIE_DATA_DIR:-D:/mini_marie_data/data}/mini_marie_cache"

if [[ ! -d "${LOCAL_DATA}" ]]; then
  echo "ERROR: local cache root not found: ${LOCAL_DATA}" >&2
  echo "Set MINI_MARIE_DATA_DIR to your warmed data root." >&2
  exit 1
fi

# Normalize Windows path when invoked from Git Bash
if command -v cygpath >/dev/null 2>&1 && [[ "${LOCAL_DATA}" == [A-Za-z]:* ]]; then
  LOCAL_DATA="$(cygpath -u "${LOCAL_DATA}")"
fi

ALL_DIRS=(sg_old chemistry twa_city)
TARGETS=("${ALL_DIRS[@]}")
if [[ $# -gt 0 ]]; then
  TARGETS=("$@")
fi

echo "Remote: ${REMOTE}:${REMOTE_DATA}"
echo "Local:  ${LOCAL_DATA}"
echo "Upload: ${TARGETS[*]}"
echo

for name in "${TARGETS[@]}"; do
  src="${LOCAL_DATA}/${name}/"
  if [[ ! -d "${src}" ]]; then
    echo "SKIP missing local dir: ${src}" >&2
    continue
  fi
  echo "==> rsync ${name}/"
  rsync -avP --mkpath "${src}" "${REMOTE}:${REMOTE_DATA}/${name}/"
done

echo
echo "Done. On zaha-01 verify with:"
echo "  ls -lh ${REMOTE_DATA}/*/"
echo "  curl -s http://127.0.0.1:8080/health/cache | python3 -m json.tool"
