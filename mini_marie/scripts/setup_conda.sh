#!/usr/bin/env bash
# Conda-based setup (no apt / no system Python venv). Safe on shared servers.
#
# From project root:
#   bash mini_marie/scripts/setup_conda.sh
#
# Optional:
#   CONDA_ENV_DIR=/home/xz378/mariecp/.conda-env
#   CONDA_PYTHON=3.10
#   INSTALL_KGQA=1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

CONDA_ENV_DIR="${CONDA_ENV_DIR:-${PROJECT_ROOT}/.conda-env}"
CONDA_PYTHON="${CONDA_PYTHON:-3.10}"

echo "==> Project root: ${PROJECT_ROOT}"
echo "==> Conda env:    ${CONDA_ENV_DIR}"

init_conda() {
  if command -v conda >/dev/null 2>&1; then
    return 0
  fi
  for base in "${CONDA_PREFIX:-}" "${HOME}/miniconda3" "${HOME}/anaconda3" "${HOME}/conda" "/opt/conda"; do
    [[ -n "${base}" && -f "${base}/etc/profile.d/conda.sh" ]] || continue
    # shellcheck disable=SC1091
    source "${base}/etc/profile.d/conda.sh"
    return 0
  done
  cat >&2 <<EOF
ERROR: conda not found in PATH.

Install Miniconda in your home (no sudo, no apt):
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash Miniconda3-latest-Linux-x86_64.sh -b -p \$HOME/miniconda3
  source \$HOME/miniconda3/etc/profile.d/conda.sh

Then re-run: bash mini_marie/scripts/setup_conda.sh
EOF
  exit 1
}

init_conda

env_ok() {
  [[ -x "${CONDA_ENV_DIR}/bin/python" ]] \
    && "${CONDA_ENV_DIR}/bin/python" -m pip --version >/dev/null 2>&1
}

if env_ok; then
  echo "==> Reusing existing conda env"
else
  echo "==> Creating conda env (python ${CONDA_PYTHON}) — no apt, no base update"
  rm -rf "${CONDA_ENV_DIR}"
  conda create -y -p "${CONDA_ENV_DIR}" "python=${CONDA_PYTHON}" pip
fi

export PATH="${CONDA_ENV_DIR}/bin:${PATH}"
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
  echo "==> Created .env from .env.example — edit REMOTE_BASE_URL / REMOTE_API_KEY"
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

cat <<EOF

Conda setup complete.

Activate for interactive use:
  export PATH=${CONDA_ENV_DIR}/bin:\$PATH
  export PYTHONPATH=${PROJECT_ROOT}

Or: conda activate ${CONDA_ENV_DIR}

EOF
