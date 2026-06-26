#!/usr/bin/env bash
# First-time Linux setup from project root (parent of mini_marie/ package).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/.venv}"

echo "==> Project root: ${PROJECT_ROOT}"

if ! command -v "${PYTHON}" >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON} not found. Install Python 3.11+ first." >&2
  exit 1
fi

PY_VER="$("${PYTHON}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "==> Using Python ${PY_VER}"

venv_ok() {
  [[ -x "${VENV_DIR}/bin/python" ]] && "${VENV_DIR}/bin/python" -m pip --version >/dev/null 2>&1
}

create_venv() {
  echo "==> Creating virtualenv at ${VENV_DIR}"
  if "${PYTHON}" -m venv "${VENV_DIR}" 2>/dev/null && venv_ok; then
    return 0
  fi
  rm -rf "${VENV_DIR}"
  echo "==> venv module unavailable; trying virtualenv package"
  if ! "${PYTHON}" -m pip --version >/dev/null 2>&1; then
    echo "ERROR: pip not found for ${PYTHON}. Install python3-pip or python${PY_VER}-venv." >&2
    return 1
  fi
  "${PYTHON}" -m pip install --user virtualenv
  "${PYTHON}" -m virtualenv "${VENV_DIR}"
  venv_ok
}

if [[ -n "${VIRTUAL_ENV:-}" && "${VIRTUAL_ENV}" == "${VENV_DIR}" ]] && venv_ok; then
  echo "==> Using active virtualenv ${VENV_DIR}"
elif venv_ok; then
  echo "==> Reusing existing virtualenv ${VENV_DIR}"
else
  rm -rf "${VENV_DIR}"
  if ! create_venv; then
    cat >&2 <<EOF
ERROR: Could not create a Python virtualenv at ${VENV_DIR}.

On Debian/Ubuntu (safe; does not affect Docker):
  sudo apt install -y python${PY_VER}-venv python3-pip
  rm -rf ${VENV_DIR}
  bash mini_marie/scripts/setup_linux.sh

Or reuse an existing env:
  python3 -m venv ${VENV_DIR}   # after apt install
  source ${VENV_DIR}/bin/activate
  INSTALL_KGQA=1 bash mini_marie/scripts/setup_linux.sh
EOF
    exit 1
  fi
fi
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip wheel

echo "==> Installing mini_marie requirements"
pip install -r requirements-mini-marie.txt

if [[ "${INSTALL_GUI:-0}" == "1" ]]; then
  echo "==> Installing GUI extras (Streamlit)"
  pip install -r requirements-gui.txt
fi

if [[ "${INSTALL_KGQA:-0}" == "1" ]]; then
  echo "==> Installing KGQA agent extras (LangChain/LangGraph)"
  pip install -r requirements-kgqa.txt
fi

echo "==> Creating runtime directories"
python - <<'PY'
from mini_marie.cache_paths import ensure_runtime_dirs
ensure_runtime_dirs()
print("Runtime directories OK")
PY

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — edit REMOTE_BASE_URL / REMOTE_API_KEY for LLM features"
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

cat <<EOF

Setup complete.

Next steps (from project root):
  cd ${PROJECT_ROOT}
  source ${VENV_DIR}/bin/activate
  export PYTHONPATH=${PROJECT_ROOT}
  ./mini_marie/scripts/verify_install.sh
  Read mini_marie/docs/DEPLOYMENT.md and mini_marie/docs/CACHE_STARTUP.md

Optional:
  INSTALL_GUI=1 ./mini_marie/scripts/setup_linux.sh
  INSTALL_KGQA=1 ./mini_marie/scripts/setup_linux.sh
  ./mini_marie/scripts/warm_cache_steps.sh city

EOF
