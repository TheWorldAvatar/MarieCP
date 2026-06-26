#!/usr/bin/env bash
# First-time or upgrade install for MarieCP demos on zaha-01.
#
# Run on the server as xz378 (after caches are under MINI_MARIE_DATA_DIR):
#   bash deploy/zaha-01/install.sh
#
# Optional env:
#   MARIECP_DIR=/home/xz378/mariecp
#   MARIECP_REPO=https://github.com/TheWorldAvatar/MarieCP.git
#   MARIECP_BRANCH=main
#   SKIP_MIRROR=1          # skip python -m demos.mirror
#   INSTALL_SYSTEMD=1      # sudo cp + enable mariecp-demo.service
#   MARIECP_PORT=8080        # loopback port (must match nginx upstream)
#   USE_CONDA=1              # default: conda env at .conda-env (no apt)
#
# Safety: does NOT run docker, docker-compose, or reload nginx. Only installs
# the dedicated mariecp-demo systemd unit when INSTALL_SYSTEMD=1.
#
set -euo pipefail

REPO_DIR="${MARIECP_DIR:-/home/xz378/mariecp}"
REPO_URL="${MARIECP_REPO:-https://github.com/TheWorldAvatar/MarieCP.git}"
BRANCH="${MARIECP_BRANCH:-main}"
DATA_DIR="${MINI_MARIE_DATA_DIR:-/home/xz378/mini_marie_data/data}"
BIND_PORT="${MARIECP_PORT:-8080}"

check_bind_port() {
  if ! command -v ss >/dev/null 2>&1; then
    return 0
  fi
  if ! ss -ltn "sport = :${BIND_PORT}" 2>/dev/null | grep -q LISTEN; then
    return 0
  fi
  local detail
  detail="$(ss -ltnp "sport = :${BIND_PORT}" 2>/dev/null || true)"
  if echo "${detail}" | grep -qE 'mariecp-demo|gunicorn.*demos\.server'; then
    echo "==> Port ${BIND_PORT} in use by mariecp gunicorn (upgrade OK)"
    return 0
  fi
  echo "ERROR: port ${BIND_PORT} is already in use (may be Docker or another stack)." >&2
  echo "${detail}" >&2
  echo "Pick a free port: MARIECP_PORT=8081 bash deploy/zaha-01/install.sh" >&2
  echo "Then point nginx upstream mariecp_demo at 127.0.0.1:\${MARIECP_PORT}." >&2
  exit 1
}

echo "==> MarieCP demo install"
echo "    repo:   ${REPO_DIR} (${BRANCH})"
echo "    caches: ${DATA_DIR}/mini_marie_cache"

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  echo "==> Cloning ${REPO_URL}"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${REPO_DIR}"
else
  echo "==> Updating existing clone"
  git -C "${REPO_DIR}" fetch origin
  git -C "${REPO_DIR}" checkout "${BRANCH}"
  git -C "${REPO_DIR}" pull --ff-only origin "${BRANCH}"
fi

cd "${REPO_DIR}"

if [[ ! -f configs/demo_local.env ]]; then
  echo "==> Writing configs/demo_local.env from production template"
  cp configs/demo_production.env.example configs/demo_local.env
fi

if [[ ! -f .env ]]; then
  echo "==> Creating .env stub — set REMOTE_API_KEY before starting the service"
  cat > .env <<'EOF'
REMOTE_BASE_URL=https://openrouter.ai/api/v1
REMOTE_API_KEY=REPLACE_ME
DEMO_LLM_MODEL=gpt-4o
FLASK_SECRET_KEY=change-me-in-production
EOF
  echo "    Edit: ${REPO_DIR}/.env"
fi

echo "==> Python env + dependencies (conda, no apt)"
export USE_CONDA="${USE_CONDA:-1}"
export INSTALL_KGQA=1

if [[ "${USE_CONDA}" == "1" ]]; then
  rm -rf .venv
  bash mini_marie/scripts/setup_conda.sh
  export PATH="${REPO_DIR}/.conda-env/bin:${PATH}"
else
  bash mini_marie/scripts/setup_linux.sh
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
pip install -r requirements-demo.txt gunicorn
chmod +x deploy/zaha-01/run_gunicorn.sh

export PYTHONPATH="${REPO_DIR}"
export MINI_MARIE_DATA_DIR="${DATA_DIR}"

echo "==> Cache layout"
python - <<'PY'
from pathlib import Path
import os

root = Path(os.environ["MINI_MARIE_DATA_DIR"]) / "mini_marie_cache"
missing = []
for name in ("sg_old", "chemistry", "twa_city"):
    sub = root / name
    dbs = sorted(sub.rglob("*.sqlite")) if sub.is_dir() else []
    if dbs:
        print(f"  OK  {name}: {dbs[0]} ({dbs[0].stat().st_size // (1024*1024)} MiB)")
    else:
        print(f"  MISSING {name} under {sub}")
        missing.append(name)
if missing:
    raise SystemExit(
        "Upload caches first: bash deploy/zaha-01/upload_caches.sh (from dev machine)"
    )
PY

if [[ "${SKIP_MIRROR:-0}" != "1" ]]; then
  echo "==> Mirroring Zaha static UI from theworldavatar.io"
  python -m demos.mirror
else
  echo "==> SKIP_MIRROR=1 — assuming demos/static/zaha already present"
fi

echo "==> Verify import + health (Flask test client)"
python - <<'PY'
import os
os.environ.setdefault("MARIE_FRONTEND_PROXY", "0")
from demos.server import app

client = app.test_client()
assert client.get("/health").status_code == 200
assert client.get("/demos/hub/").status_code == 200
print("  health + hub OK")
PY

if [[ "${INSTALL_SYSTEMD:-0}" == "1" ]]; then
  check_bind_port
  echo "==> Installing systemd unit (sudo) — mariecp-demo only, no Docker changes"
  tmp_unit="$(mktemp)"
  sed "s/MARIECP_BIND=127.0.0.1:8080/MARIECP_BIND=127.0.0.1:${BIND_PORT}/" \
    deploy/zaha-01/mariecp-demo.service > "${tmp_unit}"
  sudo cp "${tmp_unit}" /etc/systemd/system/mariecp-demo.service
  rm -f "${tmp_unit}"
  sudo systemctl daemon-reload
  sudo systemctl enable mariecp-demo
  sudo systemctl restart mariecp-demo
  sleep 2
  sudo systemctl status mariecp-demo --no-pager || true
  curl -sf "http://127.0.0.1:${BIND_PORT}/health" && echo "  gunicorn health OK"
else
  cat <<EOF

Manual next steps:
  1. Edit ${REPO_DIR}/.env (REMOTE_API_KEY required for QA/chat)
  2. Test interactively:
       cd ${REPO_DIR}
       export PATH=${REPO_DIR}/.conda-env/bin:\$PATH
       export PYTHONPATH=${REPO_DIR} MINI_MARIE_DATA_DIR=${DATA_DIR}
       gunicorn -w 2 -b 127.0.0.1:8080 --timeout 300 demos.server:app
  3. Enable service:
       INSTALL_SYSTEMD=1 bash deploy/zaha-01/install.sh
  4. Add nginx snippet: deploy/zaha-01/nginx-mariecp-demo.conf
     on www.theworldavatar.io (requires site admin / sudo)

EOF
fi

echo "==> Done."
