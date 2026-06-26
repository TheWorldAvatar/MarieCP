#!/usr/bin/env bash
# Run official Marie Next.js frontend (Linux/WSL) against MarieCP Flask API.
#
# Usage (from repo root inside WSL):
#   bash demos/run_marie_compat_wsl.sh setup    # npm install + write .env.local
#   bash demos/run_marie_compat_wsl.sh api        # Flask API only (port 8080)
#   bash demos/run_marie_compat_wsl.sh frontend   # Next dev only (port 3000)
#   bash demos/run_marie_compat_wsl.sh            # both (api in background)
#
# Open: http://127.0.0.1:3000/demos/marie/

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="${REPO_ROOT}/vendor/TheWorldAvatar/QuestionAnswering/QA_ICL/frontend/next_app_marie"
API_BASE="${MARIE_FRONTEND_API_BASE:-}"
BASE_PATH="${MARIE_FRONTEND_BASE_PATH:-/demos/marie}"
FRONTEND_PORT="${MARIE_FRONTEND_PORT:-3000}"
API_PORT="${DEMO_PORT:-8080}"

load_wsl_env() {
  export PYTHONPATH="${REPO_ROOT}"
  # Only export WSL-specific overrides here; Python loads .env via dotenv (CRLF-safe).
  if [[ -f "${REPO_ROOT}/configs/demo_local.wsl.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/configs/demo_local.wsl.env"
    set +a
  fi
}

# When Flask runs on Windows and Next in WSL, SSR must use a host IP reachable from WSL.
wsl_windows_host() {
  ip route show default 2>/dev/null | awk '{print $3; exit}'
}

default_api_base() {
  if [[ -n "${API_BASE}" ]]; then
    echo "${API_BASE}"
    return
  fi
  if [[ "${MARIE_API_ON_WINDOWS:-0}" == "1" ]]; then
    echo "http://$(wsl_windows_host):${API_PORT}/demos/marie/api"
    return
  fi
  echo "http://127.0.0.1:${API_PORT}/demos/marie/api"
}

probe_api() {
  local candidates=()
  if [[ "${MARIE_API_ON_WINDOWS:-0}" == "1" ]]; then
    candidates+=("http://$(wsl_windows_host):${API_PORT}")
    candidates+=("http://127.0.0.1:${API_PORT}")
  else
    candidates+=("http://127.0.0.1:${API_PORT}")
  fi
  for base in "${candidates[@]}"; do
    if curl -sf --connect-timeout 2 "${base}/health" >/dev/null; then
      echo "${base}/demos/marie/api"
      return 0
    fi
  done
  return 1
}

load_nvm() {
  export NVM_DIR="${HOME}/.nvm"
  # shellcheck disable=SC1091
  [ -s "${NVM_DIR}/nvm.sh" ] && . "${NVM_DIR}/nvm.sh"
}

activate_python() {
  cd "${REPO_ROOT}"
  load_wsl_env
  if [[ -f "${REPO_ROOT}/.venv-wsl/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.venv-wsl/bin/activate"
    return
  fi
  echo "Creating Linux venv at .venv-wsl..."
  if ! python3 -m venv "${REPO_ROOT}/.venv-wsl"; then
    cat >&2 <<'EOF'
ERROR: python3-venv is not installed in WSL.

One-time setup (in WSL):
  sudo apt update
  sudo apt install -y python3.12-venv python3-pip

Then rerun:
  bash demos/run_marie_compat_wsl.sh both

Alternatively run API on Windows and Next in WSL (hybrid):
  Windows:  $env:MARIE_FRONTEND_DEV='1'; $env:DEMO_HOST='0.0.0.0'; python -m demos.server
  WSL:      MARIE_API_ON_WINDOWS=1 bash demos/run_marie_compat_wsl.sh frontend
  (Hybrid requires WSL can reach Windows :8080 — allow in Windows Firewall if SSR fails.)
EOF
    exit 1
  fi
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.venv-wsl/bin/activate"
  pip install -q -U pip
  pip install -q -r "${REPO_ROOT}/requirements-demo.txt"
}

write_env_local() {
  local api
  if [[ "${MARIE_API_ON_WINDOWS:-0}" == "1" ]] && api="$(probe_api)"; then
    :
  else
    api="$(default_api_base)"
  fi
  mkdir -p "${FRONTEND}"
  cat > "${FRONTEND}/.env.local" <<EOF
# MarieCP WSL dev — official next_app_marie → MarieCP Flask API
NEXT_PUBLIC_BACKEND_ENDPOINT=${api%/}/
BASE_PATH=${BASE_PATH}
EOF
  echo "Wrote ${FRONTEND}/.env.local (API ${api%/}/)"
}

setup_frontend() {
  load_nvm
  if ! command -v node >/dev/null 2>&1; then
    echo "Node.js not found. Install in WSL (recommended):"
    echo "  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
    echo "  source ~/.bashrc && nvm install 20"
    exit 1
  fi
  if [[ ! -f "${FRONTEND}/package.json" ]]; then
    echo "Frontend missing. From repo root run: python3 -m demos.setup_marie_frontend"
    exit 1
  fi
  write_env_local
  echo "Using node $(node --version) npm $(npm --version)"
  (cd "${FRONTEND}" && npm install)
  echo "Setup complete."
}

run_api() {
  activate_python
  export MARIE_FRONTEND_DEV=1
  export DEMO_PORT="${API_PORT}"
  export DEMO_HOST="${DEMO_HOST:-0.0.0.0}"
  echo "MarieCP API http://127.0.0.1:${API_PORT}/demos/marie/api/ (CORS enabled, bind ${DEMO_HOST})"
  exec python3 -m demos.server
}

run_frontend() {
  load_nvm
  if [[ "${MARIE_API_ON_WINDOWS:-0}" == "1" ]]; then
    echo "Expecting MarieCP API on Windows: python -m demos.server (MARIE_FRONTEND_DEV=1)"
  fi
  write_env_local
  cd "${FRONTEND}"
  echo "Official Marie frontend http://127.0.0.1:${FRONTEND_PORT}${BASE_PATH}/"
  exec npm run dev -- -p "${FRONTEND_PORT}" -H 0.0.0.0
}

run_both() {
  activate_python
  export MARIE_FRONTEND_DEV=1
  export DEMO_PORT="${API_PORT}"
  export DEMO_HOST="${DEMO_HOST:-0.0.0.0}"
  python3 -m demos.server &
  API_PID=$!
  trap 'kill "${API_PID}" 2>/dev/null || true' EXIT INT TERM
  sleep 2
  echo "API pid ${API_PID} — http://127.0.0.1:${API_PORT}/demos/marie/api/"
  run_frontend
}

cmd="${1:-}"
if [[ -z "${cmd}" ]]; then
  if [[ "${MARIE_API_ON_WINDOWS:-0}" == "1" ]]; then
    cmd=frontend
  else
    cmd=both
  fi
fi
case "${cmd}" in
  setup) setup_frontend ;;
  api) run_api ;;
  frontend) MARIE_API_ON_WINDOWS="${MARIE_API_ON_WINDOWS:-0}" run_frontend ;;
  both) run_both ;;
  *)
    echo "Usage: $0 {setup|api|frontend|both}" >&2
    echo "  frontend — WSL Next only; run API on Windows (recommended if python3-venv missing)" >&2
    echo "  both     — API + Next in WSL (needs: sudo apt install python3.12-venv)" >&2
    exit 1
    ;;
esac
